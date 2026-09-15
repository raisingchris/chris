import asyncio
import base64
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

from fastapi import FastAPI
import httpx
import pytest

from agent.creative import (CreativeJobs, decode_inputs, pack_outputs, private_json,
                            valid_name, worker_config, worker_env)


@pytest.mark.parametrize('name', ['/etc/passwd', '../private', 'a/../../secret', 'a/./file',
                                  '.codex/auth.json', 'a/.hidden', 'a\\b', 'a//b', ''])
def test_reject_unsafe_input_names(name):
    with pytest.raises(ValueError):
        valid_name(name)


def payload(**extra):
    return {'id': 'a' * 32, 'brief': 'Make a sample.', 'files': [], **extra}


def test_input_validation_before_writing():
    assert decode_inputs(payload(files=[{'path': 'refs/logo.svg', 'data': 'eA=='}]))[1] == [('refs/logo.svg', b'x')]
    for files in [
        [{'path': 'same', 'data': 'eA=='}] * 2,
        [{'path': 'a', 'data': 'eA=='}, {'path': 'a/b', 'data': 'eA=='}],
        [{'path': 'output/result', 'data': 'eA=='}],
        [{'path': 'test', 'data': '!'}],
    ]:
        with pytest.raises(ValueError):
            decode_inputs(payload(files=files))


def test_worker_config_enforces_subscription_and_narrow_filesystem(monkeypatch):
    import tomllib
    monkeypatch.setenv('OPENAI_API_KEY', 'must-not-inherit')
    monkeypatch.setenv('PARENT_A_PASSWORD', 'must-not-inherit')
    c = tomllib.loads(worker_config())
    assert c['forced_login_method'] == 'chatgpt'
    assert c['model_provider'] == 'openai'
    assert c['permissions']['creative']['filesystem'][':root'] == 'deny'
    assert c['permissions']['creative']['network']['enabled'] is False
    e = worker_env(Path('/private/auth'), Path('/private/job'))
    assert 'OPENAI_API_KEY' not in e and 'PARENT_A_PASSWORD' not in e
    assert e['CODEX_HOME'] == '/private/auth'


def test_exports_only_deliverables_and_blocks_secrets_and_links(tmp_path):
    job = tmp_path/'job'; out = job/'output'; out.mkdir(parents=True)
    (job/'worker.log').write_text('private diagnostics')
    (out/'sample.svg').write_text('<svg/>')
    target = tmp_path/'files.zip'
    assert pack_outputs(job, target, []) == [{'path': 'sample.svg', 'bytes': 6}]
    with zipfile.ZipFile(target) as z:
        assert z.namelist() == ['sample.svg']
    (out/'secret.txt').write_text('Private Parent')
    with pytest.raises(ValueError, match='privacy'):
        pack_outputs(job, target, ['private parent'])
    (out/'secret.txt').unlink()
    (out/'link').symlink_to(job/'worker.log')
    with pytest.raises(ValueError, match='links'):
        pack_outputs(job, target, [])


@pytest.fixture
def jobs(tmp_path):
    cfg = SimpleNamespace(state_dir=tmp_path, canaries=[])
    s = SimpleNamespace(cfg=cfg, archive=SimpleNamespace(append=lambda *args: None))
    jobs = CreativeJobs(s, 'local-token')
    app = FastAPI()
    app.add_api_route('/jobs', jobs.submit, methods=['POST'])
    app.add_api_route('/jobs/{id}', jobs.status, methods=['GET'])
    app.add_api_route('/jobs/{id}/files', jobs.download, methods=['GET'])
    return jobs, app


def client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test',
                             headers={'Authorization': 'Bearer local-token'})


@pytest.mark.asyncio
async def test_requires_auth_and_subscription_without_api_fallback(jobs, monkeypatch):
    j, app = jobs
    monkeypatch.setenv('OPENAI_API_KEY', 'present-but-not-authorized')
    async with client(app) as c:
        assert (await c.post('/jobs', json=payload(), headers={'Authorization': ''})).status_code == 401
        assert (await c.post('/jobs', json=payload())).status_code == 503
    assert list(j.jobs.iterdir()) == []


@pytest.mark.asyncio
async def test_idempotent_submit_and_single_worker(jobs):
    j, app = jobs
    (j.home/'auth.json').write_text(json.dumps({'auth_mode': 'chatgpt', 'tokens': {'access_token': 'fake'}}))
    finish = asyncio.Event()
    calls = []
    async def run(path, brief, lease):
        calls.append(path)
        try:
            await finish.wait()
        finally:
            lease.close()
    j.run = run
    async with client(app) as c:
        r = await c.post('/jobs', json=payload()); assert r.status_code == 200
        await asyncio.sleep(0)
        assert (await c.post('/jobs', json=payload())).status_code == 200
        assert len(calls) == 1
        assert (await c.post('/jobs', json=payload(brief='Different brief'))).status_code == 409
        assert (await c.post('/jobs', json=payload(id='b'*32))).status_code == 429
        status = (await c.get('/jobs/'+'a'*32)).json()
        assert status['state'] == 'running' and 'request_hash' not in status
        assert (await c.get('/jobs/'+'a'*32+'/files')).status_code == 409
    finish.set()
    await asyncio.gather(*j.tasks)


@pytest.mark.asyncio
async def test_restart_reports_interrupted_instead_of_running_forever(jobs):
    j, app = jobs
    p = j.jobs/('a'*32); p.mkdir()
    private_json(p/'status.json', {'id': 'a'*32, 'state': 'running', 'request_hash': 'private'})
    async with client(app) as c:
        status = (await c.get('/jobs/'+'a'*32)).json()
        assert status['state'] == 'interrupted'
        assert 'request_hash' not in status


@pytest.mark.asyncio
@pytest.mark.parametrize('contents, expected', [('ordinary asset', 'done'), ('private parent', 'failed')])
async def test_worker_publishes_only_privacy_checked_outputs(jobs, monkeypatch, contents, expected):
    import sys
    from agent import creative
    j, _ = jobs
    j.services.cfg.canaries = ['private parent']
    p = j.jobs/('b'*32); work = p/'work'; (work/'output').mkdir(parents=True); (work/'tmp').mkdir()
    private_json(p/'status.json', {'id': 'b'*32, 'state': 'running'})
    real_create = asyncio.create_subprocess_exec
    async def fake_codex(*args, **kwargs):
        code = 'from pathlib import Path; Path("output/asset.txt").write_text('+repr(contents)+')'
        return await real_create(sys.executable, '-c', code, **kwargs)
    monkeypatch.setattr(creative.asyncio, 'create_subprocess_exec', fake_codex)
    lease = (j.root/'worker.lock').open('a')
    await j.run(p, 'Make sample', lease)
    meta = json.loads((p/'status.json').read_text())
    assert meta['state'] == expected and lease.closed
    if expected == 'failed':
        assert 'private parent' not in json.dumps(meta)
        assert 'files' not in meta
