# Cecoio spike report: Phases 0–3 findings and Phase 4 recommendations

Companion to [CECO-PLAN.md](CECO-PLAN.md).
Records what the initial `Ceco` architectural spike established,
and the recommendations it produced for the Phase 4 migration-seam decision.
No backend migration and no VTKHDF work were undertaken.

## Scope delivered

- New `Ceco` class in `src/meshio/_ceco.py`, exported as `meshio.Ceco`.
- `Ceco.from_meshio(mesh, copy=False)` migration helper (zero-copy share by default).
- Focused tests in `tests/test_ceco.py`.
- No changes to any reader or writer.

## Phase 0: reconnaissance findings

### How writers receive their input

`_helpers.write(filename, mesh, …)` passes the mesh object *directly* to the selected writer
and validates only by iterating `mesh.cells` to check block shapes.
`Mesh.write` is a thin delegate to `_helpers.write(path, self, …)`.

### The coupling surface is small and duck-typed

No writer performs an `isinstance(…, Mesh)` check anywhere in the tree.
Writers depend only on a structural surface:

- attributes: `points`, `cells` (list of `CellBlock`), `point_data`, `cell_data`,
  `field_data`, `point_sets`, `cell_sets`, `gmsh_periodic`, `info`;
- methods/properties: `get_cells_type`, `get_cell_data`, `point_sets_to_data`,
  `cell_sets_to_data`, `cells_dict`, `cell_data_dict`, `cell_sets_dict`.

Every one of those methods operates solely on the shared attribute surface,
so they can be reused by any structurally compatible object.

### Representative writers

- STL (`stl/_stl.py`): uses `get_cells_type` / `get_cell_data`; does not mutate its input.
- Gmsh 4.1 (`gmsh/_gmsh41.py`): attribute access only, plus `gmsh_periodic`; does not mutate.
- VTU (`vtu/_vtu.py`): mutates its input in place — replaces entries of `mesh.cells`,
  reassigns `mesh.point_data` / `mesh.cell_data` / `mesh.field_data`,
  and calls `point_sets_to_data` / `cell_sets_to_data`.
  (`vtk/_vtk_51.py` and the CLI converter share this mutation pattern.)

The mutation pattern is the only real hazard for a zero-copy neutral object
and is the key finding feeding the Phase 4 decision.

## Phase 1–2: `Ceco` design and delegation

`Ceco` is an independent class — not a subclass of `Mesh`, and it stores no `Mesh` instance.
It reuses the existing `Mesh` machinery as an implementation detail:

- construction delegates to `Mesh.__init__(self, …)` to populate the object's own attributes
  with identical validation and (where arrays already match) zero-copy semantics;
- the writer-required methods delegate to the `Mesh` implementations applied to `self`
  (for example `Mesh.get_cells_type(self, cell_type)`), with no inheritance.

`ceco.write(path)` therefore works through the unmodified `_helpers.write` dispatch,
with no explicit conversion in user code and no `.to_meshio()` step.

`from_meshio` shares `mesh`'s arrays by default; `copy=True` yields independent arrays.

## Phase 3: test results

`tests/test_ceco.py` (11 tests) covers construction from `points` + `cells`,
construction from a `Mesh`, shared-vs-copy aliasing semantics,
absence of `Mesh` inheritance, preservation of the `Mesh` API,
delegated method parity, and delegated `ceco.write` round-trips for VTU, Gmsh, and STL.

Regression check (optional backends installed via the `all` extra):

- clean tree: 25 failed, 714 passed, 6 skipped;
- with the spike: 25 failed, 725 passed, 6 skipped.

The spike adds exactly its 11 passing tests and introduces no regressions.
The 25 pre-existing failures are unrelated to `Ceco`:
they come from `np.fromfile(…, sep=" ")` in ASCII readers (Gmsh, dolfin, ugrid, raw-binary VTU)
under NumPy 2.x, and reproduce identically on the clean tree on both Python 3.12 and 3.14.

## Where the current `Mesh` API resists clean delegation

- In-place mutation by VTU / VTK 5.1 / CLI converter is the one genuine friction point.
  With zero-copy sharing, writing a `Ceco` that was built from a `Mesh` and that carries
  `point_sets` can add a key to the *shared* `point_data` dict and so be observed through the
  source `Mesh`. The spike's write tests use `copy=True` to avoid perturbing shared fixtures,
  which is the correct short-term mitigation but confirms the underlying hazard.
- The delegated methods live on `Mesh`, so `Ceco` currently depends on `Mesh` internals.
  This is acceptable for the spike but is the obvious target for the Phase 4 refactor.

## Phase 4 recommendations

1. Readers returning `Ceco`: defer. The duck-typed write path means a reader that returns a
   `Ceco` already works with every writer; the real risk is user code doing
   `isinstance(result, Mesh)`. Flip readers only behind a transition/compatibility window.
2. `Mesh` versus `Ceco`: keep both, independent, with no inheritance in either direction.
   Let `Mesh` become a thin compatibility facade over shared utilities rather than being deleted.
3. Shared free functions — the main refactor: lift `get_cells_type`, `get_cell_data`,
   `point_sets_to_data`, `cell_sets_to_data`, and the `*_dict` properties out of `Mesh` into a
   shared module operating on the attribute surface, and have both `Mesh` and `Ceco` call them.
   This removes `Ceco`'s dependency on `Mesh` internals.
4. Structural typing: introduce a `MeshLike` `typing.Protocol` capturing the writer contract,
   and type writers against it to document the seam.
5. Writer capability / loss reporting: defer; add a lightweight per-writer feature declaration
   plus a check that warns or errors, rather than a large negotiation framework.
6. Writer mutation: fix VTU, VTK 5.1, and the CLI converter to operate on local copies instead
   of mutating their input. This benefits `Mesh` today and removes the zero-copy hazard for
   `Ceco`; it can land as a small follow-up independent of the seam decision.
7. Package rename `meshio` → `cecoio`: defer until the seam is stable and readers return `Ceco`,
   keeping a `meshio` import alias during the transition.

## Environment note

Python is invoked through `uv`; `uv` resolves CPython 3.14 by default here, which is above the
project's current supported ceiling (3.12). The suite was exercised on both 3.12 and 3.14 with
identical results. The pre-existing `np.fromfile` failures are a separate NumPy-2.x compatibility
issue worth addressing independently of this spike.

## Status

First milestone met: an ordinary mesh can be represented as an independent `Ceco` and written
through existing meshio machinery without explicit user conversion, with existing behaviour intact.
Pause here for architectural review before any package-wide migration or VTKHDF work.
