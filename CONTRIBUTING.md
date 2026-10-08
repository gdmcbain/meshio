# meshio contributing guidelines

The meshio community appreciates your contributions via issues and
pull requests. Note that the [code of conduct](CODE_OF_CONDUCT.md)
applies to all interactions with the meshio project, including
issues and pull requests.

When submitting pull requests, please follow the style guidelines of
the project, ensure that your code is tested and documented, and write
good commit messages, e.g., following [these
guidelines](https://chris.beams.io/posts/git-commit/).

By submitting a pull request, you are licensing your code under the
project [license](LICENSE.txt) and affirming that you either own copyright
(automatic for most individuals) or are authorized to distribute under
the project license (e.g., in case your employer retains copyright on
your work).

## Testing

Cecoio is an interchange library,
so its tests must establish that external formats are read and written correctly,
not merely that our own code is self-consistent.
The full rationale is in [doc/plans/CECOIO-TESTING-PRINCIPLES.md](doc/plans/CECOIO-TESTING-PRINCIPLES.md).

Five rules:

1. Never use our reader as the primary oracle for our writer, or vice versa.
2. Test readers against independently produced, authoritative fixtures.
3. Test writers with independent consumers, specifications, or reviewed golden files.
4. Keep round trips, but treat them as information-preservation tests, not proof of format conformance.
5. Test `Ceco` as a neutral representation independently of individual formats.

### Test layout

The suite is organized by the question each test answers:

```text
tests/
    unit/         # Ceco and other core behaviour, no file I/O
    readers/      # authoritative fixture -> reader -> expected semantics
    writers/      # known Ceco -> writer -> golden/independent check
    roundtrip/    # information preservation across write/reread
    conformance/  # checked against external reference implementations
    data/         # fixtures, each with recorded provenance
```

The ordinary `pytest` run uses checked-in fixtures and reviewed goldens
and must not require installing every supported mesh ecosystem.
The `conformance/` suite may depend on external tools (Gmsh, VTK, MED, ...)
and is intended for dedicated or scheduled CI jobs.

### Baseline before regressions

Before attributing a failure to a change, run the suite against the unmodified baseline
and classify each failure as a pre-existing baseline failure or a new regression.
Fix only regressions as part of unrelated work;
characterise and repair baseline failures deliberately and separately.
See [issue #1](https://github.com/gdmcbain/meshio/issues/1)
for the current inherited NumPy 2.x ASCII-reader baseline failures.
Do not weaken tests or expand a change's scope to make pre-existing failures disappear.
