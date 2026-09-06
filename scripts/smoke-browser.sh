#!/usr/bin/env bash
# Smoke test for Chris's browser. Run on the box as `chris` (or as brain via
# `sudo -u chris -H PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers /app/scripts/smoke-browser.sh`).
# Prints the title of example.com if Playwright + Chromium are usable by this user.
set -euo pipefail
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/opt/pw-browsers}"
python3 - <<'EOF'
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://example.com", timeout=30_000)
    print(page.title())
    browser.close()
EOF
