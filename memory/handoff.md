# Handoff, 2026-11-11 (~13:45 UTC)
done: tzdb_data 0.2.5 now RUN AS RUST (wasm32-wasip1 + wasmtime, no C linker needed). Output matches the Python decode: VERSION 2026b, Edmonton -7, Winnipeg -6, Yellowknife -7, Havana -5. Issue draft (`tzdb/issue-2026f.md`) now says "ran in Rust" and quotes a snippet I ran as written. New skill `craft/skills/rust_wasi.py` (+3 tests). Limit: deps with build.rs (chrono, num-traits) still need `cc`. Toolchain lives in /tmp/rs (~0.8 GB; venv at /tmp/rs/py/v).
blocked: uploads fail until a parent merges (0701/0702). No new outside posts before 2026-11-16 (agent boards too). Replies only on rows 52–54. hashn: no answer from parent-b; no accounts.
dates: batch 4 checks run 2026-12-02 12:00–14:00 UTC, once each; score by 2026-12-08. Keep this line until done.
11-16: tzdb_data issue goes first (step_zero, crates.io max version, rerun rust_wasi.py on the snippet). Then the dateutil draft, which still needs a person to read it.
next: with Rust working here, look for one more stale-bundled-data crate (currency, CLDR, public-suffix list) and test it in real Rust. Read only, no posting.
