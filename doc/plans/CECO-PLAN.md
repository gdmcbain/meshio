# Cecoio: Initial Fork and Migration Plan

## Purpose

Fork `meshio` into a maintained scientific mesh/interchange library whose neutral representation can grow beyond the assumptions of `meshio.Mesh` without sacrificing the simple API that makes meshio useful.

The initial goal is deliberately conservative: introduce a new neutral `Ceco` representation alongside the existing `Mesh`, preserve existing behaviour and tests, and establish a migration path. Do **not** attempt to design or implement every conceivable geometric entity in the first iteration.

The immediate motivating use case is transient finite-element output on a fixed mesh, including eventual first-class VTKHDF support. However, the initial `Ceco` design must not be shaped solely around VTKHDF.

## Background and design motivation

The conceptual precedent is Netpbm: rather than implement pairwise conversions among every pair of formats, translate each external format to and from a common neutral representation. This changes the conversion problem from a complete graph with O(n^2) relationships into a hub-and-spoke problem with O(n) format adapters.

`meshio.Mesh` already serves this role successfully for a large and useful subset of scientific meshes. `Ceco` should preserve that strength while leaving room for richer geometry, topology, hierarchy, nonconformity, and field representations when actual formats or use cases require them.

The name `Ceco` derives from **CEll COmplex**. The package name is `cecoio`, for **CEll COmplex Input/Output**. The term is an inspiration for the neutral model, not a requirement that every `Ceco` satisfy a particular mathematical definition of a regular cell complex or CW complex.

## Core design principles

### 1. `Ceco` is the future neutral representation

`Ceco` should eventually become the common intermediate representation used by readers and writers.

A `meshio.Mesh` should be naturally representable by a `Ceco`. The converse need not always hold: future `Ceco` objects may contain information that `meshio.Mesh` cannot represent.

Do **not** model this relationship using inheritance:

```python
class Ceco(meshio.Mesh):
    ...
```

is specifically *not* the intended architecture.

Inheritance would assert that every possible `Ceco` is a `meshio.Mesh` and would make the existing `Mesh` data model a permanent ceiling on `Ceco`.

### 2. Prefer structural compatibility and delegation

For the ordinary meshio-compatible subset, a `Ceco` should provide the familiar API directly:

```python
ceco.points
ceco.cells
ceco.point_data
ceco.cell_data
ceco.field_data
ceco.point_sets
ceco.cell_sets
```

Existing meshio functionality should be reused through structural compatibility, refactoring, adapters, or internal delegation as appropriate.

Users should **not** ordinarily need to write code such as:

```python
ceco.to_meshio().write(...)
```

Instead, the desired user-facing experience is:

```python
ceco.write(...)
```

The fact that an operation is initially implemented by existing meshio machinery should be an implementation detail.

### 3. Preserve the simple `points` + `cells` common case

Do not make the overwhelmingly common case more abstract merely to accommodate hypothetical future geometry.

The normal API should remain as direct and familiar as:

```python
ceco.points
ceco.cells
```

A user's existing meshio-oriented code should require as little conceptual change as practical.

### 4. Geometry and cells are conceptually distinct

The long-term model should not define geometry to mean only a table of point coordinates.

Conceptually, geometric entities may include points, curves, surfaces, or other entities embedded or otherwise anchored in an ambient coordinate space. Possible future representations might include parametric geometry, implicit or level-set geometry, splines/NURBS, and others.

Cells are distinct: they describe discrete/topological entities and their connectivity, incidence, or association with geometry.

For v0, however, **do not implement curves, surfaces, arbitrary-dimensional geometry, or a general geometry hierarchy**. The purpose of documenting the distinction now is to avoid implementation decisions that make those extensions unnecessarily breaking later.

### 5. Design for richer geometry, but do not implement it yet

The initial `Ceco` should largely support the information already represented by `meshio.Mesh`.

Do not add speculative APIs such as:

```python
ceco.geometry.entities[2]
ceco.curves
ceco.surfaces
```

until a concrete format or use case requires them and thereby teaches us what their representation should be.

At the same time, avoid documenting or coding `Ceco` as if its semantic definition were permanently "a points array plus cell blocks".

### 6. Represent first; validate at boundaries

`Ceco` is an interchange representation, not a finite-element mesh validator.

Do not require every `Ceco` to be:

- conforming;
- manifold;
- regular;
- simplicial;
- suitable for a particular finite-element method;
- representable by every supported file format.

Nonconforming meshes, including meshes with hanging nodes or more general coarse/fine interfaces, are legitimate use cases.

A source reader should preserve information that its source format can represent. A target writer should determine whether the particular `Ceco` can be represented faithfully in its target format.

Validation should therefore be layered and capability-oriented rather than enforced by an overly restrictive `Ceco` constructor.

### 7. Do not reduce the neutral representation to the lowest common denominator

The long-term `Ceco` model should be capable of becoming more expressive than any one backend.

It is acceptable for a valid `Ceco` to be writable by only a subset of formats, or even by no currently implemented format while it is being manipulated in memory.

Writers should eventually be able to distinguish among:

1. features they can represent faithfully;
2. features that may be deliberately dropped with an explicit policy/warning;
3. features whose loss should cause a clear error.

Do not implement a large capability framework in the first iteration, but avoid making one impossible later.

### 8. Preserve existing meshio behaviour during migration

The fork inherits a large collection of mature readers, writers, tests, and user expectations. Treat these as an asset.

Do not begin with a repository-wide `Mesh` -> `Ceco` or `meshio` -> `cecoio` search-and-replace.

The first implementation should introduce `Ceco` alongside the existing `Mesh`, discover the actual coupling between the current readers/writers and `Mesh`, and refactor incrementally.

## Repository preparation

Start from the existing `gdmcbain/meshio` fork, synchronized with `nschloe/meshio` upstream `main`.

Suggested setup, assuming conventional remotes:

```bash
git remote -v
git fetch upstream
git switch main
git merge --ff-only upstream/main
git push origin main
git switch -c ceco
git push -u origin ceco
```

If the `upstream` remote is absent:

```bash
git remote add upstream https://github.com/nschloe/meshio.git
git fetch upstream
```

Do not rename the GitHub repository or Python package at the outset. Preserve the obvious meshio ancestry while the architectural spike is underway.

## Phase 0: reconnaissance

Before changing production code, inspect the repository and answer these questions in a short development note or issue:

1. Which `meshio.Mesh` attributes are assumed directly by each major reader/writer helper?
2. Which functions insist on `isinstance(..., Mesh)` or otherwise couple to the concrete class?
3. Which methods on `Mesh` are merely conveniences over free functions?
4. Which pieces of `Mesh` contain representation logic versus general operations?
5. Can representative writers operate on a structurally compatible object without modification?
6. Where does mutation of `Mesh` objects occur, and does that affect delegation/view strategies?
7. Which existing tests provide the best regression coverage for a minimally invasive architectural spike?

Do not refactor broadly during reconnaissance.

## Phase 1: introduce `Ceco`

Add a small independent `Ceco` class.

Its first implementation should support the meshio-compatible information needed for representative ordinary meshes. Start with the existing `Mesh` data vocabulary rather than inventing new geometry abstractions.

A plausible initial surface is:

```python
Ceco(
    points,
    cells,
    point_data=None,
    cell_data=None,
    field_data=None,
    point_sets=None,
    cell_sets=None,
    # Add other existing Mesh information only as required.
)
```

Requirements:

- `Ceco` must **not** subclass `Mesh`.
- Keep the constructor and data access unsurprising for existing meshio users.
- Prefer NumPy arrays and existing `CellBlock` machinery where reuse does not restrict the future model unnecessarily.
- Do not add curves, surfaces, generalized geometry, hierarchy, or nonconforming constraints yet.
- Avoid unnecessary copying when creating a `Ceco` from existing meshio data.
- Do not make a permanent `meshio.Mesh` instance the authoritative internal storage of every `Ceco`.

### Compatibility construction

Provide an internal or public migration helper for creating a `Ceco` from an existing `Mesh`. Whether the eventual public spelling is `Ceco.from_meshio(mesh)` can remain provisional during the spike.

For the ordinary case, prefer zero-copy/shared-array construction unless the caller requests a copy or correctness requires one.

Explicitly test the aliasing/copy semantics so they are not accidental.

## Phase 2: delegate representative existing functionality

Prove that users of an ordinary Ceco can access useful existing meshio functionality without explicit conversion in application code.

At minimum, demonstrate:

```python
ceco.write(path)
```

for a small representative set of existing formats.

Good initial candidates are formats exercising different code paths, for example:

- Gmsh MSH;
- VTK/VTU;
- STL or another simple surface format.

Prefer making existing functions operate against the required protocol/attributes where that is clean. Where not clean, use a narrow internal adapter or delegation mechanism.

Do not expose an explicit `.to_meshio()` call as the primary user workflow.

The spike should help determine whether an internal meshio-compatible view remains useful. If one exists, keep it narrow and clearly non-authoritative.

## Phase 3: regression and compatibility tests

The existing meshio test suite should continue to pass.

Add focused tests for `Ceco` covering at least:

1. construction from ordinary `points` and `cells`;
2. existing data dictionaries and sets used by the chosen representative formats;
3. construction from an existing `Mesh`;
4. copy versus shared-data behaviour;
5. delegated writing to representative existing formats;
6. rereading those files and comparing significant mesh information;
7. absence of inheritance from `meshio.Mesh`;
8. preservation of the existing `meshio.Mesh` API.

Tests should compare semantic content rather than byte-for-byte serialization unless a format specifically requires deterministic byte output.

## Phase 4: decide the migration seam

After the spike works, stop and document what was learned before migrating every backend.

In particular decide:

- whether readers should begin returning `Ceco` directly;
- whether `Mesh` becomes a compatibility facade, remains alongside `Ceco`, or is deprecated eventually;
- how much of existing `Mesh` functionality should move to free functions/shared utilities;
- whether structural protocols should be formalized using `typing.Protocol`;
- how writer capability/loss reporting should eventually work;
- when the Python import/package name should change from `meshio` to `cecoio`.

Do not decide these purely from aesthetics before exercising representative real backends.

## Phase 5: VTKHDF

Only after the core `Ceco` architectural spike is sound, add VTKHDF support.

The motivating acceptance case is a transient finite-element solution on a fixed unstructured mesh:

- mesh geometry/topology stored once where the VTKHDF format permits it;
- multiple physical times;
- changing point and/or cell fields for each time step;
- one `.vtkhdf` artifact where practical;
- readable by current VTK/PyVista tooling;
- no I/O coupled to the numerical time-stepping loop itself.

Keep transient-data concerns separate from the first `Ceco` class unless implementing VTKHDF reveals a genuine requirement for the neutral representation.

Prefer an open-source dependency stack. Investigate whether a small direct HDF5 implementation using `h5py` is appropriate, while following the published VTKHDF specification and official examples rather than inventing a private layout. Compare this against using the Python VTK bindings before committing the backend architecture.

## Non-goals for the initial spike

Do not initially:

- rename every `meshio` symbol or directory;
- delete `Mesh`;
- subclass `Mesh` from `Ceco` or vice versa merely for code reuse;
- implement curves or surfaces;
- implement arbitrary-dimensional geometric entities;
- design a universal CAD/B-rep model;
- implement FEM shape functions or isoparametric mappings in Ceco;
- require conforming meshes;
- implement a full mathematical cell-complex validator;
- add an elaborate backend capability negotiation framework;
- rewrite all readers/writers before the representative spike succeeds;
- allow VTKHDF requirements to dictate the entire neutral model.

## Desired user experience

For an ordinary mesh, aim to preserve meshio's simplicity:

```python
import cecoio

ceco = cecoio.read("mesh.msh")

print(ceco.points)
print(ceco.cells)

ceco.write("mesh.vtu")
```

Eventually, a supported transient workflow might be comparably direct, but do not freeze that API before the VTKHDF spike establishes the right shape.

## Architectural invariant

Keep this relationship in mind throughout the work:

```text
ordinary meshio.Mesh  --->  naturally representable as Ceco

Ceco                   -/->  not necessarily representable as meshio.Mesh
```

Therefore code reuse must not turn `meshio.Mesh` into the permanent ontology beneath `Ceco`.

## First Copilot task

Please begin with reconnaissance and the smallest architectural spike, not a broad rewrite.

1. Inspect `src/meshio/_mesh.py`, format helpers, and representative writers.
2. Summarize concrete coupling to `Mesh` before modifying it.
3. Add an independent minimal `Ceco` class sufficient to represent an ordinary existing mesh.
4. Add focused tests for construction and compatibility.
5. Make one or two existing writer paths work with `Ceco` through structural compatibility or narrow internal delegation.
6. Keep all existing tests green.
7. Report any places where the current `Mesh` API prevents clean delegation before generalizing the approach.

Prefer small, reviewable commits. Do not migrate all backends until the spike demonstrates that the proposed boundary is sound.

## Success criterion for the first milestone

The milestone is successful when an ordinary existing mesh can be represented as an independent `Ceco`, can use representative existing meshio functionality such as writing a file **without explicit user conversion**, and the existing meshio behaviour remains intact.

At that point, pause for architectural review before proceeding to package-wide migration or VTKHDF.
