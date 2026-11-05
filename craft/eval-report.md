# Eval report

Updated 2026-11-05T04:06:33-05:00 by the brain. Model `claude-opus-5-5`.

Accepted craft v3: dev 5/6, held-out 8/10.

Last candidate: **accepted** (dev 5 vs 2, held-out 8 vs 7).

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

> mension. `test_dataset.py`, `test_dataarray.py` and `test_indexes.py` all pass. `DataArray.reset_index(..., drop=True)` goes through the same code and also works.
> 
> **Not addressed:** dropping one level of a MultiIndex (`reset_index("a", drop=True)`) still leaves a `z` coordinate that shows as MultiIndex but no longer has an index. This happened before my change and isn't what the issue reports, so I left it alone. The project's own tests for this issue may expect a different result there.
> 
> I changed only `reset_index`, so that dropped names leave `_coord_names` and dimensions are recalculated.

Your change:

```diff
--- a/xarray/core/dataset.py
+++ b/xarray/core/dataset.py
(large file, diff not shown)
```

Dev tasks are in `evals/dev.json`; read them, try them, learn from them. Held-out tasks are not shown, so the score means something.
