# Eval report

Updated 2026-11-19T04:05:26-05:00 by the brain. Model `claude-opus-5-5`.

Accepted craft v3: dev 5/6, held-out 8/10.

Last candidate: **rejected** (held-out 7 < 8).

| dev task | kind | passed | note |
|---|---|---|---|
| sympy__sympy-16597 | fix | yes |  |
| sphinx-doc__sphinx-9229 | fix | yes |  |
| sympy__sympy-18199 | fix | yes |  |
| pydata__xarray-6992 | fix | no | 11 of 12 issue tests still fail (xarray/tests/test_dataarray.py::TestDataArray::test_reset_index, xarray/tests/test_dataset.py::TestDataset::test_reset_index, xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[foo-False-dropped0-converted0-renamed0], xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[foo-True-dropped1-converted1-renamed1], xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[x-False-dropped2-converted2-renamed2]) |
| sphinx-doc__sphinx-7748 | fix | yes |  |
| sympy__sympy-13974 | fix | yes |  |

## pydata__xarray-6992: 11 of 12 issue tests still fail (xarray/tests/test_dataarray.py::TestDataArray::test_reset_index, xarray/tests/test_dataset.py::TestDataset::test_reset_index, xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[foo-False-dropped0-converted0-renamed0], xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[foo-True-dropped1-converted1-renamed1], xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[x-False-dropped2-converted2-renamed2])

Your last line:

> ssue's example, the single-index drop case, and `DataArray.reset_index(..., drop=True)` (which goes through the Dataset method). All four related test files pass: `test_dataset.py`, `test_dataarray.py`, `test_indexes.py` and `test_formatting.py` (865 passed, exit code 0). I did not add a test of my own to the test files.
> 
> **Not addressed:** resetting a single level (`reset_index("a", drop=True)`) still leaves a `z` coordinate shown as a MultiIndex. That behaviour was there before my change and the issue doesn't mention it, so I left it alone; the maintainers' hidden tests might still cover it.

Your change:

```diff
--- a/xarray/core/dataset.py
+++ b/xarray/core/dataset.py
(large file, diff not shown)
```

Dev tasks are in `evals/dev.json`; read them, try them, learn from them. Held-out tasks are not shown, so the score means something.
