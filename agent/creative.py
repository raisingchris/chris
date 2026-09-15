"""Private subscription-funded Codex production jobs; no Platform API fallback."""
from __future__ import annotations

import asyncio
import base64
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import signal
import stat
import struct
import shutil
import time
import zipfile

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse

from agent.paths import safe_path

MODEL = "gpt-6-astra"
MAX_INPUT = 20_000_000
MAX_OUTPUT = 100_000_000
MAX_FILES = 200
JOB_ID = re.compile(r"^[a-f0-9]{32}$")
INSTRUCTIONS = """You are Chris's private production helper. Create and verify actual files for the
brief using GPT-6 Astra. Your workspace contains only this job's supplied inputs.
Use Blender, FFmpeg, Python, SVG and the built-in image generation tool as needed.
Built-in image generation uses the connected subscription; never use a Platform
API key or paid external service. No generative-video service is connected.
Use Blender/FFmpeg for animation and editing. Use small renders, at most two CPU
threads, and keep memory modest. Do not contact clients, submit proposals, access
accounts, inspect credentials, or request broader permissions. Network access
for shell commands is disabled. Ask for missing inputs instead of inventing them.
Put deliverables and editable source files in output/. Keep intermediate files
outside output/. Include output/RESULT.md with checks and material limitations.
Label demonstration work as sample work. Do not put machine paths, account data,
or authentication details in outputs. An unavailable tool is a limitation, not
a reason to pretend a file was generated.
"""


def private_json(path: Path, value):
    temp = path.with_suffix('.tmp')
    with temp.open('w') as f:
        json.dump(value, f)
    temp.chmod(0o600)
    temp.replace(path)


def valid_name(name):
    if not isinstance(name, str) or not name or len(name) > 240 or '\\' in name:
        raise ValueError('Invalid input filename')
    p = PurePosixPath(name)
    if p.is_absolute() or any(x in ('', '.', '..') or x.startswith('.') for x in name.split('/')):
        raise ValueError('Use ordinary relative filenames')
    return p


def decode_inputs(body):
    if not isinstance(body, dict) or not JOB_ID.fullmatch(str(body.get('id', ''))):
        raise ValueError('Provide a 32-character job id')
    brief = body.get('brief')
    if not isinstance(brief, str) or not brief.strip() or len(brief.encode()) > 40_000:
        raise ValueError('Provide a brief of at most 40,000 bytes')
    files = body.get('files', [])
    if not isinstance(files, list) or len(files) > MAX_FILES:
        raise ValueError('Too many input files')
    seen, result, size = set(), [], 0
    for item in files:
        name = str(valid_name(item['path']))
        if name in seen or name.split('/')[0] in {'output', 'tmp', 'BRIEF.md'}:
            raise ValueError('Duplicate or reserved input filename')
        seen.add(name)
        data = base64.b64decode(item['data'], validate=True)
        size += len(data)
        if size > MAX_INPUT:
            raise ValueError('Inputs exceed 20 MB')
        result.append((name, data))
    # Reject file/directory collisions before writing anything.
    for name in seen:
        if any(str(parent) in seen for parent in PurePosixPath(name).parents):
            raise ValueError('Conflicting input paths')
    return brief, result


def worker_config():
    return '''default_permissions = "creative"
approval_policy = "never"
forced_login_method = "chatgpt"
cli_auth_credentials_store = "file"
model_provider = "openai"
model_reasoning_effort = "medium"
web_search = "disabled"
[features]
apps = false
plugins = false
[permissions.creative.filesystem]
":root" = "deny"
":minimal" = "read"
"/usr/local" = "read"
"/opt/pw-browsers" = "read"
[permissions.creative.filesystem.":workspace_roots"]
"." = "write"
[permissions.creative.network]
enabled = false
'''


def worker_env(home: Path, job: Path):
    # Construct from scratch: no API keys, parent secrets, marketplace tokens,
    # local machine paths, or inherited Codex provider configuration.
    return {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': str(job / 'home'),
            'CODEX_HOME': str(home), 'LANG': 'C.UTF-8', 'TZ': 'UTC',
            'TMPDIR': str(job / 'tmp'), 'OMP_NUM_THREADS': '2',
            'OPENBLAS_NUM_THREADS': '2', 'PLAYWRIGHT_BROWSERS_PATH': '/opt/pw-browsers'}


def clean_png_metadata(data: bytes) -> bytes:
    """Drop identifying PNG metadata without decoding or changing image pixels."""
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        return data
    result, pos = bytearray(data[:8]), 8
    while pos < len(data):
        if pos + 12 > len(data):
            raise ValueError('Truncated PNG')
        size = struct.unpack('>I', data[pos:pos + 4])[0]
        end = pos + 12 + size
        if end > len(data):
            raise ValueError('Truncated PNG chunk')
        kind = data[pos + 4:pos + 8]
        if kind not in {b'tEXt', b'zTXt', b'iTXt', b'eXIf', b'tIME'}:
            result.extend(data[pos:end])
        pos = end
        if kind == b'IEND':
            break
    return bytes(result)


def pack_outputs(job: Path, target: Path, canaries):
    root = job / 'output'
    if not root.is_dir() or root.is_symlink():
        raise ValueError('No output directory')
    total, names = 0, []
    private_terms = [x.encode().lower() for x in canaries if x]
    private_terms += [b'/users/', b'/home/brain', b'/data/state/', b'"access_token"', b'"refresh_token"']
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in sorted(root.rglob('*')):
            if p.is_symlink():
                raise ValueError('Output links are not allowed')
            if p.is_dir():
                continue
            info = p.stat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError('Only ordinary output files are allowed')
            name = str(valid_name(p.relative_to(root).as_posix()))
            total += info.st_size
            if total > MAX_OUTPUT or len(names) >= MAX_FILES:
                raise ValueError('Outputs exceed the download limit')
            data = clean_png_metadata(p.read_bytes())
            if any(term in data.lower() or term in name.encode().lower() for term in private_terms):
                raise ValueError('Output withheld by the privacy check')
            z.writestr(name, data)
            names.append({'path': name, 'bytes': len(data)})
    if not names:
        raise ValueError('No deliverables produced')
    return names


class CreativeJobs:
    def __init__(self, services, token):
        self.services = services
        self.root = Path(services.cfg.state_dir) / 'creative'
        self.root.mkdir(mode=0o700, exist_ok=True)
        self.home = self.root / 'codex'
        self.home.mkdir(mode=0o700, exist_ok=True)
        self.jobs = self.root / 'jobs'
        self.jobs.mkdir(mode=0o700, exist_ok=True)
        # Neutral private workspace paths keep parent-storage names out of native
        # project formats (Blender embeds its current filename in saved scenes).
        self.work_root = Path(services.cfg.state_dir).parent / 'production'
        self.work_root.mkdir(mode=0o700, exist_ok=True)
        self.work_root.chmod(0o700)
        self.token = token
        self.tasks = set()
        self.lock = asyncio.Lock()

    def authenticate(self, request):
        if not hmac.compare_digest(request.headers.get('authorization', ''), 'Bearer ' + self.token):
            raise HTTPException(401, 'Creative worker authentication required')

    def job_path(self, id):
        if not JOB_ID.fullmatch(id):
            raise HTTPException(404, 'Job not found')
        p = self.jobs / id
        if not p.is_dir():
            raise HTTPException(404, 'Job not found')
        return p

    def ready(self):
        try:
            auth = json.loads((self.home / 'auth.json').read_text())
            return auth.get('auth_mode') == 'chatgpt' and bool((auth.get('tokens') or {}).get('access_token'))
        except (OSError, ValueError):
            return False

    async def health(self, request: Request):
        self.authenticate(request)
        return {'ready': self.ready(), 'model': MODEL, 'billing': 'subscription',
                'worker_version': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12],
                'tools': {name: bool(shutil.which(name)) for name in ('codex', 'blender', 'ffmpeg')}}

    async def submit(self, request: Request):
        self.authenticate(request)
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > 28_000_000:
                raise HTTPException(413, 'Inputs exceed the upload limit')
        try:
            body = json.loads(raw)
            brief, files = decode_inputs(body)
        except (ValueError, KeyError, TypeError):
            raise HTTPException(400, 'Invalid brief, filenames or input files') from None
        if not self.ready():
            raise HTTPException(503, 'Subscription login needs parent attention; no API fallback is enabled')
        if shutil.disk_usage(self.root).free < 500_000_000:
            raise HTTPException(507, 'Creative storage needs cleanup; ask a parent')
        id = body['id']
        digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        async with self.lock:
            existing = self.jobs / id
            if existing.exists():
                meta = json.loads((existing / 'status.json').read_text())
                if meta['request_hash'] != digest:
                    raise HTTPException(409, 'Job id already belongs to another brief')
                return {'id': id, 'state': meta['state'], 'billing': 'subscription', 'model': MODEL}
            # Cross-process lock prevents duplicate production workers, including
            # overlap with an old service during maintenance.
            lease = (self.root / 'worker.lock').open('a')
            try:
                fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                lease.close()
                raise HTTPException(429, 'A creative job is running; retry when it finishes') from None
            try:
                existing.mkdir(mode=0o700)
                work = self.work_root / id
                work.mkdir(mode=0o700)
                (existing / 'work').symlink_to(work, target_is_directory=True)
                (work / 'tmp').mkdir()
                (work / 'home').mkdir()
                (work / 'output').mkdir()
                for name, data in files:
                    p = work / name
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(data)
                (work / 'BRIEF.md').write_text(brief)
                private_json(existing / 'status.json', {'id': id, 'state': 'running',
                             'request_hash': digest, 'started': time.time(), 'model': MODEL, 'billing': 'subscription'})
                task = asyncio.create_task(self.run(existing, brief, lease))
                self.tasks.add(task)
                task.add_done_callback(self.tasks.discard)
            except BaseException:
                lease.close()
                raise
        return {'id': id, 'state': 'running', 'billing': 'subscription', 'model': MODEL}

    async def status(self, id: str, request: Request):
        self.authenticate(request)
        p = self.job_path(id)
        meta = json.loads((p / 'status.json').read_text())
        # A process exit/restart must not leave a job claiming to run forever.
        if meta['state'] == 'running':
            with (self.root / 'worker.lock').open('a') as lease:
                try:
                    fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    meta.update(state='interrupted', message='Worker restarted; ask a parent to recover partial files')
                    private_json(p / 'status.json', meta)
                except BlockingIOError:
                    pass
        return {k: v for k, v in meta.items() if k != 'request_hash'}

    async def download(self, id: str, request: Request):
        self.authenticate(request)
        p = self.job_path(id)
        meta = json.loads((p / 'status.json').read_text())
        if meta['state'] != 'done':
            raise HTTPException(409, 'Verified files are not ready')
        return FileResponse(p / 'deliverables.zip', media_type='application/zip', filename='deliverables.zip')

    async def run(self, p, brief, lease):
        meta = json.loads((p / 'status.json').read_text())
        process = None
        try:
            # Config and auth remain outside the tool sandbox and Chris's user.
            (self.home / 'config.toml').write_text(worker_config())
            work = (p / 'work').resolve()
            (work / 'home').mkdir(exist_ok=True)
            env = worker_env(self.home, work)
            command = ['codex', 'exec', '--strict-config', '--ephemeral', '--ignore-rules',
                       '--skip-git-repo-check', '--model', MODEL, '--cd', str(work), '--json', '-']
            with (p / 'worker.log').open('wb') as log:
                process = await asyncio.create_subprocess_exec(*command, cwd=work, env=env,
                    stdin=asyncio.subprocess.PIPE, stdout=log, stderr=log, start_new_session=True)
                try:
                    await asyncio.wait_for(process.communicate((INSTRUCTIONS + '\n' + brief).encode()), timeout=900)
                finally:
                    # Kill any render children too, even if Codex exited first.
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    await process.wait()
            if process.returncode != 0:
                raise RuntimeError('Worker did not complete')
            files = await asyncio.to_thread(pack_outputs, work, p / 'deliverables.zip', self.services.cfg.canaries)
            meta.update(state='done', files=files)
        except BaseException as exc:
            # Never send raw Codex logs, OAuth errors, account data or paths to Chris.
            meta.update(state='failed', message='Job could not complete; ask a parent to inspect private diagnostics')
            (p / 'failure.txt').write_text(type(exc).__name__ + ': ' + str(exc)[:500])
        finally:
            meta['finished'] = time.time()
            private_json(p / 'status.json', meta)
            lease.close()
            self.services.archive.append('creative_job', {'id': meta['id'], 'state': meta['state'],
                                         'model': MODEL, 'billing': 'subscription'})


def register_creative(app, services):
    if services.cfg.dry_run:
        return
    root = Path(services.cfg.state_dir) / 'creative'
    root.mkdir(mode=0o700, exist_ok=True)
    token_path = root / 'worker_token'
    if token_path.exists():
        token = token_path.read_text().strip()
    else:
        token = secrets.token_urlsafe(32)
        fd = os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(token)
    access = safe_path(services.cfg.repo_dir, 'memory/inbox/.creative/access.json')
    access.parent.mkdir(parents=True, exist_ok=True)
    access.parent.chmod(0o2770)
    fd = os.open(access, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o640)
    with os.fdopen(fd, 'w') as f:
        json.dump({'base_url': 'http://127.0.0.1:8091/creative', 'token': token,
                   'model': MODEL, 'billing': 'subscription'}, f)
    access.chmod(0o640)
    jobs = CreativeJobs(services, token)
    app.add_api_route('/creative/status', jobs.health, methods=['GET'])
    app.add_api_route('/creative/jobs', jobs.submit, methods=['POST'])
    app.add_api_route('/creative/jobs/{id}', jobs.status, methods=['GET'])
    app.add_api_route('/creative/jobs/{id}/files', jobs.download, methods=['GET'])
    app.state.creative_jobs = jobs


def main():
    # A local-only service can restart independently of Chris's main sitting.
    # Its supervisor restarts it on the next boot as well.
    from types import SimpleNamespace
    from fastapi import FastAPI
    import uvicorn
    from agent.config import Config
    from agent.archive import Archive
    cfg = Config.from_env()
    services = SimpleNamespace(cfg=cfg, archive=Archive(cfg.archive_dir, tz=cfg.tz))
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    register_creative(app, services)
    uvicorn.run(app, host="127.0.0.1", port=8091, access_log=False)


if __name__ == '__main__':
    main()
