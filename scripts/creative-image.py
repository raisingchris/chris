#!/usr/bin/env python3
"""Generate one private PNG: creative-image.py PROMPT_FILE OUTPUT.png [--size 1024x1024]."""
import argparse
import base64
import json
from pathlib import Path
import sys

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt_file")
    parser.add_argument("output")
    parser.add_argument("--size", choices=["1024x1024", "1536x1024", "1024x1536"], default="1024x1024")
    args = parser.parse_args()
    root = Path("/data/repo/memory/inbox/work").resolve()
    prompt, output = Path(args.prompt_file).resolve(), Path(args.output).resolve()
    if not prompt.is_relative_to(root) or not output.is_relative_to(root) or output.suffix.lower() != ".png":
        parser.error("Keep the prompt and output PNG inside memory/inbox/work/.")
    if output.exists():
        parser.error("Output already exists; choose a new name.")
    cfg = json.loads(Path("/data/repo/memory/inbox/.creative/access.json").read_text())
    with httpx.Client(timeout=300, follow_redirects=False) as client:
        r = client.post(cfg["base_url"] + "/images/generations",
                        headers={"Authorization": "Bearer " + cfg["token"]},
                        json={"prompt": prompt.read_text(), "size": args.size})
        if r.status_code != 200:
            print("Image generation failed (HTTP %s); check the creative budget or ask a parent." % r.status_code,
                  file=sys.stderr)
            return 1
        data = base64.b64decode(r.json()["data"][0]["b64_json"], validate=True)
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("The generation service did not return PNG data.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as f:
        f.write(data)
    print(json.dumps({"output": str(output.relative_to(root)), "bytes": len(data)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
