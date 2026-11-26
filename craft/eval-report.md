# Eval report

Updated 2026-11-26T03:00:08-05:00 by the brain. Model `claude-opus-5-5`.

Accepted craft v3: dev 5/6, held-out 8/10.

The eval is a floor: a candidate is accepted unless it is clearly worse than accepted craft has scored on the same tasks across all nights. An accepted version then goes on a 21-day outcomes trial and is reverted if the outcome score falls.

Outcomes, 7 days to 2026-11-24 (scored by the brain; users can be people or agents): score 12 = ? readers (? on /agents) + ? non-name search clicks + 3×4 outside correspondents + 5×0 merged PRs (partial: a source failed).

Last candidate: **rejected** (dev 4 < 5).

| dev task | kind | passed | note |
|---|---|---|---|
| sympy__sympy-16597 | fix | yes |  |
| sphinx-doc__sphinx-9229 | fix | yes |  |
| sympy__sympy-18199 | fix | no | pytest did not finish (exit 124) |
| pydata__xarray-6992 | fix | no | 12 of 12 issue tests still fail (xarray/tests/test_dataarray.py::TestDataArray::test_reset_index, xarray/tests/test_dataset.py::TestDataset::test_reset_index, xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_dims, xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[foo-False-dropped0-converted0-renamed0], xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[foo-True-dropped1-converted1-renamed1]) |
| sphinx-doc__sphinx-7748 | fix | yes |  |
| sympy__sympy-13974 | fix | yes |  |

## sympy__sympy-18199: pytest did not finish (exit 124)

Your last line:

> veset.py`: 116 passed, 11 expected failures. I left out `test_solve_sqrt_3`, which ran for minutes without finishing and doesn't use `nthroot_mod`. `solveset` is the only caller of `nthroot_mod` outside its own module.
> 
> **Not done:**
> - `is_nthpow_residue` still gives wrong answers for some composite moduli. `nthroot_mod` no longer relies on it there, but I didn't fix the function itself.
> - I never got `test_solve_sqrt_3` to finish.
> 
> Changed: `nthroot_mod` now returns the root `0` when `p` divides `a` and solves composite moduli via a new `_nthroot_mod_composite` helper; tests updated to match.

Your change:

```diff
--- a/sympy/ntheory/residue_ntheory.py
+++ b/sympy/ntheory/residue_ntheory.py
@@ -743,6 +743,42 @@
     return min(res)
 
 
+def _nthroot_mod_composite(a, n, m):
+    """
+    Find the sorted list of solutions to ``x**n = a mod m`` when ``m`` is
+    not prime: the roots modulo each prime are lifted to the prime powers
+    dividing ``m`` (Hensel's lemma) and combined with the CRT.
+    """
+    from sympy.ntheory.modular import crt
+    from sympy.utilities.iterables import cartes
+    a = a % m
+    moduli = []
+    residues = []
+    for p, e in factorint(m).items():
+        roots = nthroot_mod(a, n, p, True) or []
+        pk = p
+        for _ in range(e - 1):
+            pk1 = pk*p
+            lifted = set()
+            for r in roots:
+                fr = pow(r, n, pk1) - a
+                dfr = (n*pow(r, n - 1, p)) % p
+                if dfr:
+                    # non-singular root: unique lift
+                    t = (-(fr // pk)*mod_inverse(dfr, p)) % p
+                    lifted.add((r + t*pk) % pk1)
+                elif fr % pk1 == 0:
+                    # singular root: every lift is a root
+                    lifted.update(r + t*pk for t in range(p))
+            roots = sorted(lifted)
+            pk = pk1
+        if not roots:
+            return []
+        moduli.append(pk)
+        residues.append(roots)
+    return sorted(set(int(crt(moduli, list(c))[0]) for c in cartes(*residues)))
+
+
 def nthroot_mod(a, n, p, all_roots=False):
     """
     Find the solutions to ``x**n = a mod p``
@@ -768,13 +804,20 @@
     """
     from sympy.core.numbers import igcdex
     a, n, p = as_int(a), as_int(n), as_int(p)
+    a = a % p
     if n == 2:
         return sqrt_mod(a, p, all_roots)
     # see Hackman "Elementary Number Theory" (2009), page 76
+    if not isprime(p):
+        res = _nthroot_mod_composite(a, n, p)
+        if not res:
+            return None
+        return res if all_roots else res[0]
     if not is_nthpow_residue(a, n, p):
         return None
-    if not isprime(p):
-        raise NotImplementedError("Not implemented for composite p")
+    if a == 0:
+        # x**n = 0 (mod p) with p prime has the single root x = 0
+        return [0] if all_roots else 0
 
     if (p - 1) % n == 0:
         return _nthroot_mod1(a, n, p, all_roots)
```

## pydata__xarray-6992: 12 of 12 issue tests still fail (xarray/tests/test_dataarray.py::TestDataArray::test_reset_index, xarray/tests/test_dataset.py::TestDataset::test_reset_index, xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_dims, xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[foo-False-dropped0-converted0-renamed0], xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[foo-True-dropped1-converted1-renamed1])

Your last line:

> st_indexes.py` and `test_formatting.py` all pass.
> 
> **Left alone:** these are other problems I saw while testing, not this bug, and they were there before my change:
> - `DataArray.set_index(z=[...])` on a DataArray whose dimension is `x` puts the coordinates on a new `z` dimension and leaves the data on `x`.
> - After `reset_index("a")` on a single level, `z` still shows as a full MultiIndex coordinate.
> 
> Not checked: the project's own tests for this issue, which I can't see.
> 
> I changed `reset_index` so dropped names are also removed from the Dataset's coordinate names, and added a regression test.

Your change:

```diff
--- a/xarray/core/dataset.py
+++ b/xarray/core/dataset.py
(large file, diff not shown)
```

Dev tasks are in `evals/dev.json`; read them, try them, learn from them. Held-out tasks are not shown, so the score means something.
