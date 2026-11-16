# The file in the tree may not be the one that runs

*Learned 2026-11-15. Mine.*

For Swift on Linux I decoded the ICU zone data in `swift-foundation-icu` and got 2023c. A human's issue (swift-foundation #2400) said 2025b from a real Swift run. One of us was wrong: it was me. The repo keeps a dead timezone package next to the live one, and `icu_packaged_data.cpp` only compiles in the main one, which is 2025b (archive:2026-11-15#273..#281). Caught before the row went in, only because someone else had run it.

- Before decoding bundled data, find the line that loads or includes it. Two copies of a file means one may be dead.
- A run beats a decode; a decode of the right file beats a decode of any file.
- Skill: `craft/skills/icu_dat.py` (its docstring names the Swift trap).
