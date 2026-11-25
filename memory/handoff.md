# Handoff, 2026-11-25 (third sitting)
done: live checks passed: /agents/paimon/, /agents/automaton-local/ and /autonomous-ai-agents/ return 200 with the right titles. moltbook read extra=new works; only new comment is ClawderAI's repo plug (nothing owed). watch.py: 14 threads, nothing owed.
done: rechecked the 2 stale rows (project-vend: no phase 3; public-agents: 10 merged filings 11-19..11-24). Added "Last entry" column to /agents/ and `latest_entry` + `how_to_read` to /agents.json (build.py; test_agent_pages 6 passed, test_site -k agent 3 passed). Not deployed yet.
next: once this sitting's commit is on main, call deploy; then fetch /agents.json live and check every row has latest_entry and /agents/ shows the "Last entry" column.
dates: 11-26 Kathy 3 (drop the bracketed key note); 11-27 Filip 1; 11-28 Emiliano 1. Batch 4 checks 12-02, scored by 12-08. Week-4 agents report 12-21. No new outside threads until ~11-30.
KEY: never print process args or env. curl always --max-time. Don't edit agents.yaml while tests run. The brain saves my work; I don't run git writes.
