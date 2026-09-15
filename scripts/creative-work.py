#!/usr/bin/env python3
"""Submit a private subscription-funded job: creative-work.py JOB_DIR BRIEF_FILE."""
import argparse
import base64
import io
import json
from pathlib import Path
import sys
import time
import uuid
import zipfile

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job_dir')
    parser.add_argument('brief_file')
    args = parser.parse_args()
    root = Path('/data/repo/memory/inbox/work').resolve()
    job, brief = Path(args.job_dir).resolve(), Path(args.brief_file).resolve()
    if job == root or not job.is_relative_to(root) or not brief.is_relative_to(job):
        parser.error('Keep this job and its brief inside memory/inbox/work/JOB/.')
    cfg = json.loads(Path('/data/repo/memory/inbox/.creative/access.json').read_text())
    if cfg.get('billing') != 'subscription':
        parser.error('Subscription worker is not configured; no API fallback is enabled.')
    receipt = job / '.creative-job.json'
    with httpx.Client(timeout=120, follow_redirects=False,
                      headers={'Authorization': 'Bearer ' + cfg['token']}) as client:
        if receipt.exists():
            id = json.loads(receipt.read_text())['id']
        else:
            files, total = [], 0
            for p in sorted(job.rglob('*')):
                rel = p.relative_to(job)
                if any(x.startswith('.') for x in rel.parts) or rel.parts[0] in ('output', 'tmp', 'home', 'deliverables'):
                    continue
                if p.is_symlink():
                    parser.error('Use ordinary input files, not symbolic links.')
                if not p.is_file() or p == brief:
                    continue
                data = p.read_bytes()
                total += len(data)
                if total > 20_000_000 or len(files) >= 200:
                    parser.error('Inputs exceed 20 MB or 200 files; reduce this job.')
                files.append({'path': rel.as_posix(), 'data': base64.b64encode(data).decode()})
            id = uuid.uuid4().hex
            payload = {'id': id, 'brief': brief.read_text(), 'files': files}
            # Save the id before submitting: a dropped response can be recovered
            # without unknowingly running and charging the same task twice.
            receipt.write_text(json.dumps({'id': id, 'state': 'submitting'}))
            try:
                response = client.post(cfg['base_url'] + '/jobs', json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (400, 401, 413, 429, 503):
                    receipt.unlink()
                print('Creative submission failed (HTTP %s). Retry later or ask a parent.' % exc.response.status_code)
                return 1
        print(json.dumps({'id': id, 'model': cfg['model'], 'billing': 'subscription'}), flush=True)
        deadline = time.monotonic() + 960
        while time.monotonic() < deadline:
            response = client.get(cfg['base_url'] + '/jobs/' + id)
            if response.status_code == 404:
                print('Submission was not recorded. Remove .creative-job.json and retry this brief.')
                return 1
            response.raise_for_status()
            status = response.json()
            if status['state'] == 'done':
                output = job / 'deliverables'
                if output.exists():
                    print('Deliverables already exist; inspect them before downloading again.')
                    return 0
                response = client.get(cfg['base_url'] + '/jobs/' + id + '/files')
                response.raise_for_status()
                with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                    for info in z.infolist():
                        path = Path(info.filename)
                        if path.is_absolute() or any(x in ('.', '..') or x.startswith('.') for x in path.parts):
                            raise ValueError('Unsafe output filename')
                    output.mkdir()
                    z.extractall(output)
                receipt.write_text(json.dumps(status))
                print(json.dumps({'state': 'done', 'output': str(output.relative_to(root)), 'files': status['files']}))
                return 0
            if status['state'] != 'running':
                print(json.dumps(status))
                return 1
            time.sleep(10)
        print('Still processing. Run the same command again to collect this job without resubmitting.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
