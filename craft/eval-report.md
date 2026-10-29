# Eval report

Updated 2026-10-28T23:21:02-04:00 by the brain. Model `claude-opus-5-5`.

Accepted craft v2: dev 6/6, held-out 8/8.

Last candidate: **accepted** (dev 6 vs 5, held-out 8 vs 8).

| dev task | passed | fails on bug | passes with fix | note |
|---|---|---|---|---|
| psf__requests-1142 | yes | True | True |  |
| pytest-dev__pytest-7432 | yes | True | True |  |
| sympy__sympy-15017 | yes | True | True |  |
| sphinx-doc__sphinx-9367 | yes | True | True |  |
| pydata__xarray-4629 | yes | True | True |  |
| pylint-dev__pylint-7080 | yes | True | True |  |

Dev tasks are in `evals/dev.json`; read them, try them, learn from them. Held-out tasks are not shown, so the score means something.
