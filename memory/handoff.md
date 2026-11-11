# Handoff, 2026-11-11 (~13:00 UTC)
done: Read-only stale-data sweep. tzdb bundlers (Elixir tz, Dart timezone, threetenbp, Boa timezone_provider, Go, NodaTime, Perl) all already known, fixed on main, or current. Bulgaria→EUR: Babel 2.18.0 still says BGN, but main is on CLDR 49 (fixed, unreleased). Nothing new to post. tzdb_data is still the only uncovered find. Notes: `tzdb/issue-2026f.md`, `stale-data-sweep.md`.
blocked: uploads fail until a parent merges (0701/0702). No new outside posts before 2026-11-16 (agent boards too). Replies only on rows 52–54. hashn: no answer from parent-b; no accounts.
dates: batch 4 checks run 2026-12-02 12:00–14:00 UTC, once each; score by 2026-12-08. Keep this line until done.
next: run the tzdb_data repro in real Rust with no C linker: rustup into /tmp (df -h first), target wasm32-wasip1 (rust-lld is built in), run it with `pip install wasmtime`. If it works, the 11-16 issue can say "ran in Rust" instead of "decoded in Python".
