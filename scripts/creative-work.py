#!/usr/bin/env python3
"""Run Astra in a private job folder: creative-work.py JOB_DIR BRIEF_FILE."""
import argparse
import json
import os
import signal
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_dir")
    parser.add_argument("brief_file")
    args = parser.parse_args()
    root = Path("/data/repo/memory/inbox/work").resolve()
    job = Path(args.job_dir).resolve()
    if not job.is_relative_to(root) or job == root:
        parser.error("Use a job folder inside memory/inbox/work/.")
    job.mkdir(parents=True, exist_ok=True)
    brief = Path(args.brief_file).resolve()
    if not brief.is_relative_to(root):
        parser.error("Keep the brief in the private work folder.")
    prompt = brief.read_text()
    connection = json.loads(Path("/data/repo/memory/inbox/.creative/access.json").read_text())
    # No personal Codex session/config, parent API key, billing key, GH token or
    # other agent credentials are inherited by this child process.
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/home/chris", "LANG": "C.UTF-8",
           "TZ": "America/New_York", "CODEX_HOME": str(job / ".codex"),
           "CHRIS_CREATIVE_TOKEN": connection["token"],
           "PLAYWRIGHT_BROWSERS_PATH": "/opt/pw-browsers"}
    Path(env["CODEX_HOME"]).mkdir(exist_ok=True)
    command = ["codex", "exec", "--ephemeral", "--ignore-user-config", "--skip-git-repo-check",
               "--sandbox", "workspace-write", "--model", connection["model"], "--cd", str(job),
               "-c", "sandbox_workspace_write.network_access=true",
               "-c", 'model_provider="chris"', "-c", 'model_reasoning_effort="medium"',
               "-c", 'model_providers.chris.name="Chris creative worker"',
               "-c", 'model_providers.chris.base_url=' + json.dumps(connection["base_url"]),
               "-c", 'model_providers.chris.env_key="CHRIS_CREATIVE_TOKEN"',
               "-c", 'model_providers.chris.wire_api="responses"',
               "-c", 'model_providers.chris.supports_websockets=false',
               "--json", "--output-last-message", str(job / "RESULT.md"), "-"]
    instructions = ("You are Chris's private production helper, using GPT-6 Astra. Create and verify actual files "
        "for the brief, not just advice. Work only inside this job folder. Use installed Blender, FFmpeg, "
        "Python, SVG and Playwright as appropriate. For generated raster images, write a prompt file and call "
        "python /app/scripts/creative-image.py PROMPT_FILE OUTPUT.png (one medium-quality Flare image). "
        "A separate generative-video API is not connected; make video with Blender/FFmpeg or explain the gap. "
        "Do not contact clients, submit proposals, change "
        "accounts, spend elsewhere or inspect credentials. Keep client inputs private. Label sample work "
        "as sample work. Leave a concise RESULT.md listing output files, checks, limitations and next steps.\n\n")
    try:
        process = subprocess.Popen(command, env=env, stdin=subprocess.PIPE, text=True,
                                   cwd=job, start_new_session=True)
        process.communicate(instructions + prompt, timeout=900)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        print("Creative task timed out; inspect partial files before retrying.", file=sys.stderr)
        return 1
    return process.returncode


if __name__ == "__main__":
    sys.exit(main())
