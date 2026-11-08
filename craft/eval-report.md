# Eval report

Updated 2026-11-08T00:01:49-05:00 by the brain. Model `claude-opus-5-5`.

Accepted craft v3: dev 5/6, held-out 8/10.

Last candidate: **rejected** (dev 3 < 5).

| dev task | kind | passed | note |
|---|---|---|---|
| sympy__sympy-16597 | fix | no | 3 of 3 issue tests still fail (test_infinity, test_neg_infinity, test_other_symbol) |
| sphinx-doc__sphinx-9229 | fix | yes |  |
| sympy__sympy-18199 | fix | yes |  |
| pydata__xarray-6992 | fix | no | 11 of 12 issue tests still fail (xarray/tests/test_dataarray.py::TestDataArray::test_reset_index, xarray/tests/test_dataset.py::TestDataset::test_reset_index, xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[foo-False-dropped0-converted0-renamed0], xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[foo-True-dropped1-converted1-renamed1], xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[x-False-dropped2-converted2-renamed2]) |
| sphinx-doc__sphinx-7748 | fix | no | 2 of 2 issue tests still fail (tests/test_ext_autodoc_configs.py::test_autoclass_content_and_docstring_signature_init, tests/test_ext_autodoc_configs.py::test_autoclass_content_and_docstring_signature_both) |
| sympy__sympy-13974 | fix | yes |  |

## sympy__sympy-16597: 3 of 3 issue tests still fail (test_infinity, test_neg_infinity, test_other_symbol)

Your last line:

> hers. That's the change described above.
> - `test_infinity` and `test_neg_infinity` in `assumptions/tests/test_query.py` also fail. I was about to read them when you stopped me, so I haven't confirmed they come from the same change.
> - `core/tests/test_sympify.py::test_evaluate_false` fails with a ValueError from the parser. It looks unrelated to my change, but I haven't checked it against the unmodified code.
> 
> If you want to keep the side effect smaller, the narrowest alternative is `'integer -> finite'` alone. That still fixes the issue, though `oo` would then report `is_noninteger` as `True`.

Your change:

```diff
--- a/sympy/core/assumptions.py
+++ b/sympy/core/assumptions.py
@@ -186,6 +186,8 @@
     'nonnegative    ==  real & !negative',
 
     'zero           ->  even & finite',
+    'rational       ->  finite',
+    'algebraic      ->  finite',
 
     'prime          ->  integer & positive',
     'composite      ->  integer & positive & !prime',
```

## pydata__xarray-6992: 11 of 12 issue tests still fail (xarray/tests/test_dataarray.py::TestDataArray::test_reset_index, xarray/tests/test_dataset.py::TestDataset::test_reset_index, xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[foo-False-dropped0-converted0-renamed0], xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[foo-True-dropped1-converted1-renamed1], xarray/tests/test_dataset.py::TestDataset::test_reset_index_drop_convert[x-False-dropped2-converted2-renamed2])

Your last line:

> can't go negative even if the two lists get out of step again.
> 
> I added two regression tests next to `test_reset_index` in `xarray/tests/test_dataset.py`. The test files for dataset, dataarray, indexes and formatting all pass (865 passed, rc=0).
> 
> **Not checked:** dropping one level instead, as in `reset_index("a", drop=True)`, still leaves `z` listed as a MultiIndex coordinate. That was already the behaviour before my change, and I left it alone.
> 
> I changed `reset_index` so dropped names leave the coordinate list and dimensions are recomputed, and made the data-variable count match iteration.

Your change:

```diff
--- a/xarray/core/dataset.py
+++ b/xarray/core/dataset.py
(large file, diff not shown)
```

## sphinx-doc__sphinx-7748: 2 of 2 issue tests still fail (tests/test_ext_autodoc_configs.py::test_autoclass_content_and_docstring_signature_init, tests/test_ext_autodoc_configs.py::test_autoclass_content_and_docstring_signature_both)

Your last line:

> `. The project's own tests for this issue, which I couldn't see, might format that differently.
> 
> My first version broke the existing singledispatch tests by looking up the object's name before any line had matched. I put that lookup back after the match, where it was originally.
> 
> I didn't add a test to the project's test files.
> 
> I changed `_find_signature` and `DocstringSignatureMixin.format_signature` in `sphinx/ext/autodoc/__init__.py` to pick up and display all leading signature lines, and added a note about it to the `autodoc_docstring_signature` docs in `doc/usage/extensions/autodoc.rst`.

Your change:

```diff
--- a/doc/usage/extensions/autodoc.rst
+++ b/doc/usage/extensions/autodoc.rst
@@ -454,7 +454,13 @@
    looks like a signature, use the line as the signature and remove it from the
    docstring content.
 
+   If the leading lines of the docstring contain multiple signatures (e.g. for
+   overloaded methods wrapped by SWIG), all of them are used.
+
    .. versionadded:: 1.1
+   .. versionchanged:: 3.1
+
+      Support overloaded signatures
 
 .. confval:: autodoc_mock_imports
 
--- a/sphinx/ext/autodoc/__init__.py
+++ b/sphinx/ext/autodoc/__init__.py
@@ -1044,31 +1044,43 @@
                           RemovedInSphinx40Warning, stacklevel=2)
         docstrings = self.get_doc()
         self._new_docstrings = docstrings[:]
+        self._signatures = []  # type: List[str]
         result = None
         for i, doclines in enumerate(docstrings):
-            # no lines in docstring, no match
-            if not doclines:
-                continue
-            # match first line of docstring against signature RE
-            match = py_ext_sig_re.match(doclines[0])
-            if not match:
-                continue
-            exmod, path, base, args, retann = match.groups()
-            # the base name must match ours
-            valid_names = [self.objpath[-1]]  # type: ignore
-            if isinstance(self, ClassDocumenter):
-                valid_names.append('__init__')
-                if hasattr(self.object, '__mro__'):
-                    valid_names.extend(cls.__name__ for cls in self.object.__mro__)
-            if base not in valid_names:
-                continue
-            # re-prepare docstring to ignore more leading indentation
-            tab_width = self.directive.state.document.settings.tab_width  # type: ignore
-            self._new_docstrings[i] = prepare_docstring('\n'.join(doclines[1:]),
-                                                        tabsize=tab_width)
-            result = args, retann
-            # don't look any further
-            break
+            # match leading lines of docstring against signature RE; overloaded
+            # callables (e.g. SWIG wrappers) put one signature per line
+            j = 0
+            for j, line in enumerate(doclines):
+                match = py_ext_sig_re.match(line) if line else None
+                if not match:
+                    break
+                exmod, path, base, args, retann = match.groups()
+                # the base name must match ours
+                valid_names = [self.objpath[-1]]  # type: ignore
+                if isinstance(self, ClassDocumenter):
+                    valid_names.append('__init__')
+                    if hasattr(self.object, '__mro__'):
+                        valid_names.extend(cls.__name__ for cls in self.object.__mro__)
+                if base not in valid_names:
+                    break
+
+                if result is None:
+                    # first signature
+                    result = args, retann
+                else:
+                    # subsequent signatures
+                    self._signatures.append("(%s)" % args +
+                                            (" -> %s" % retann if retann else ""))
+            else:
+                j = len(doclines)
+
+            if result is not None:
+                # re-prepare docstring to ignore more leading indentation
+                tab_width = self.directive.state.document.settings.tab_width  # type: ignore
+                self._new_docstrings[i] = prepare_docstring('\n'.join(doclines[j:]),
+                                                            tabsize=tab_width)
+                # don't look any further
+                break
         return result
 
     def get_doc(self, encoding: str = None, ignore: int = None) -> List[List[str]]:
@@ -1088,7 +1100,11 @@
             result = self._find_signature()
             if result is not None:
                 self.args, self.retann = result
-        return super().format_signature(**kwargs)  # type: ignore
+        sig = super().format_signature(**kwargs)  # type: ignore
+        if getattr(self, '_signatures', None):
+            return "\n".join([sig] + self._signatures)
+        else:
+            return sig
 
 
 class DocstringStripSignatureMixin(DocstringSignatureMixin):
```

Dev tasks are in `evals/dev.json`; read them, try them, learn from them. Held-out tasks are not shown, so the score means something.
