# Ceco spike follow-up: stabilize the Mesh/Ceco compatibility seam

## Summary

The initial `Ceco` architectural spike succeeded: an independent `Ceco` can represent ordinary meshio data and use representative existing writer paths without inheriting from `Mesh`.

The inherited NumPy 2.x test failures identified during the spike have now been fixed separately under Issue #1. **Treat the current `ceco` branch as the clean baseline for this issue.** Do not carry forward the spike report's earlier allowance for 25 baseline failures.

This issue graduates the successful spike into a small, maintainable compatibility seam between `Mesh`, `Ceco`, and the existing writer infrastructure.

## Architectural direction

`Ceco` is intended to become the more general neutral representation.

For the ordinary meshio-compatible subset, both `Mesh` and `Ceco` should satisfy the structural interface required by existing mesh writers.

Neither class should inherit from the other at this stage.

Conceptually:

```text
                 MeshLike
                 protocol
                 /      \
              Mesh      Ceco
                \        /
                 \      /
             shared operations
                    |
              existing writers
```

The important relationship is structural compatibility, not class inheritance.

In particular, do not introduce either:

```python
class Ceco(Mesh):
    ...
```

or:

```python
class Mesh(Ceco):
    ...
```

as part of this issue.

Whether `Mesh` might eventually become a restricted subtype, compatibility facade, alias, or independent legacy representation can be decided later, after more migration experience.

## Findings from the spike

The spike established that:

- existing representative writers can largely operate on a mesh-shaped object by duck typing;
- no writer performs an `isinstance(..., Mesh)` check;
- no broad conversion API is required merely to use existing writer functionality;
- `Ceco` therefore need not expose `.to_meshio()` as the normal user workflow;
- some reusable operations currently live as `Mesh` methods even though they are structurally applicable to `Ceco`;
- the spike provisionally reuses some `Mesh` implementation by explicitly calling methods such as `Mesh.__init__(...)` and `Mesh.get_cells_type(...)`;
- some existing writer/conversion paths mutate data belonging to their input object;
- zero-copy/shared-array construction makes unexpected input mutation particularly important.

The provisional cross-calls into `Mesh` were useful for the spike but should not become the long-term architecture.

## Goals

### 1. Extract genuinely shared operations

Identify functionality currently implemented as `Mesh` methods that does not intrinsically depend on a concrete `Mesh` instance.

Candidate operations identified by the spike include:

- `get_cells_type`;
- `get_cell_data`;
- `cells_dict`;
- `cell_data_dict`;
- `cell_sets_dict`;
- `point_sets_to_data`;
- `cell_sets_to_data`;
- common constructor normalization needed by both `Mesh` and `Ceco`.

Move appropriate implementation into shared functions or helpers used by both classes.

The desired direction is:

```text
               shared implementation
                 /             \
              Mesh             Ceco
```

rather than:

```text
                 Mesh
                  ^
                  |
            implementation reuse
                  |
                 Ceco
```

Do not duplicate substantial implementations between `Mesh` and `Ceco` merely to avoid cross-calls.

### 2. Remove provisional `Ceco -> Mesh` implementation dependence

After extracting shared implementation, `Ceco` should not depend on calls such as:

```python
Mesh.__init__(self, ...)
Mesh.get_cells_type(self, ...)
```

`Mesh` and `Ceco` may share implementation, but neither should need to masquerade as an instance of the other.

### 3. Establish writer non-mutation as an invariant

Serialization should be observational with respect to its input object: writing a file may create filesystem output and temporary derived representations, but should not change the supplied `Mesh` or `Ceco`.

Adopt the principle:

> **Writers may observe their input; writers shall not mutate their input.**

In practical terms, after:

```python
ceco.write("result.vtu")
```

`ceco` should contain the same information it contained before the call.

This does **not** mean that `Ceco` itself must be immutable. User-requested changes such as:

```python
ceco.point_data["temperature"] = temperature
```

may be perfectly legitimate. The rule is specifically that serialization must not introduce surprising side effects.

The spike identified mutation in the relevant VTU, VTK 5.1, and CLI conversion paths. Refactor those paths so transformations required by an output format operate on writer-owned/local derived state rather than on the input object.

Do not solve this merely by deep-copying the complete input before every write. Scientific meshes may be large, and serialization should not require a full duplicate merely to protect the input.

Prefer copying only the state a writer needs to transform. For example, if a writer needs to add format-specific data to a mapping, use an appropriate local copy of the mapping. If an underlying NumPy array itself must be transformed in place, create a derived array rather than modifying an array shared with the input.

This matters particularly because `Ceco.from_meshio(mesh, copy=False)` intentionally permits data sharing. A mutating writer must not cause action-at-a-distance changes to the source `Mesh` through shared dictionaries or NumPy arrays.

Writer order should consequently not alter semantics. For example, these two sequences should not differ because the first writer changed the shared object:

```python
ceco.write("mesh.vtu")
ceco.write("mesh.msh")
```

and:

```python
ceco.write("mesh.msh")
ceco.write("mesh.vtu")
```

### 4. Add explicit writer non-mutation tests

Turn the rule above into regression tests rather than relying on convention.

For representative writers, snapshot the relevant observable state, write the file, and assert that the input is unchanged.

Cover at least:

- `points`;
- `cells` and their connectivity arrays;
- `point_data`;
- `cell_data`;
- `field_data` where relevant;
- `point_sets` and `cell_sets` where relevant.

Tests should be sensitive to both top-level container mutation and mutation of shared nested NumPy arrays. A shallow copy of a dictionary is not sufficient evidence of non-mutation if the arrays referenced by the dictionary remain shared and can be modified in place.

Pay particular attention to the zero-copy case:

```python
mesh = ...
ceco = Ceco.from_meshio(mesh, copy=False)
ceco.write(path)
```

Writing `ceco` must not mutate either `ceco` or state observable through the source `mesh` merely because the two deliberately share data.

Tests should target the specific observable attributes rather than requiring a general-purpose `Ceco.__eq__` solely for this purpose.

### 5. Define the existing writer contract with a protocol

Consider introducing a `typing.Protocol`, provisionally named something like:

```python
MeshLike
```

to document the structural interface actually required by existing writers.

The protocol should be derived from observed writer requirements, not from hypothetical future `Ceco` functionality.

It should therefore describe the compatibility seam, not define the ontology of `Ceco`.

Keep it as small as practical.

Do not add speculative members for future curves, surfaces, arbitrary geometry, hierarchy, or other capabilities not required by current writer implementations.

If extracting the shared operations leaves the contract sufficiently clear without a formal protocol, document that finding rather than adding a `Protocol` merely to match the architectural sketch.

### 6. Preserve zero-copy interoperability where practical

The spike demonstrated useful sharing between existing mesh data and `Ceco`.

Preserve inexpensive construction/conversion where correctness permits it.

Document and test whether arrays and containers are:

- shared;
- shallow-copied;
- or deeply copied.

Copying semantics should be deliberate rather than an incidental consequence of implementation.

## Testing baseline

Issue #1 has been rectified on the current `ceco` branch. The inherited 25 NumPy 2.x failures reported by the original spike are therefore **no longer an accepted baseline condition**.

Before modifying production code for this issue:

1. record the current `ceco` commit;
2. run the complete configured test suite;
3. confirm that it is green, apart from any deliberately documented skips/xfails;
4. use that exact result as the regression baseline for Issue #2.

For this issue:

- no new failures should be introduced relative to that baseline;
- existing `Mesh` behaviour should remain intact;
- existing `Ceco` spike tests should continue to pass;
- add focused tests for extracted shared operations;
- add writer non-mutation regression tests;
- test the structural writer contract if a `MeshLike` protocol is introduced.

The existing writer round-trip tests are useful compatibility/information-preservation tests, but they are not independent proof of file-format conformance. Do not use Cecoio's own reader as the primary oracle for Cecoio's writer when independent conformance testing is later added.

Do not weaken tests merely to obtain a green suite.

## Non-goals

This issue does **not** include:

- changing all readers to return `Ceco`;
- deprecating or deleting `Mesh`;
- deciding the final inheritance relationship between `Mesh` and `Ceco`;
- renaming the Python package from `meshio` to `cecoio`;
- moving the project to a new GitHub repository;
- implementing curves, surfaces, or generalized geometry;
- implementing nonconforming-mesh constraints or hierarchy;
- adding VTKHDF support;
- designing a complete backend-capability framework;
- revisiting the now-fixed Issue #1 except if this work genuinely exposes a regression in that fix;
- rewriting every backend around `Ceco`.

Keep this as a small follow-up to the architectural spike.

## Acceptance criteria

This issue is complete when:

- [ ] The pre-change test suite on the current `ceco` baseline is recorded and green apart from deliberately documented skips/xfails.
- [ ] `Ceco` remains independent of `Mesh` inheritance.
- [ ] `Mesh` does not need to inherit from `Ceco`.
- [ ] Provisional calls from `Ceco` directly into `Mesh` implementation have been replaced by appropriate shared implementation.
- [ ] Existing representative writers continue to accept ordinary `Ceco` objects without explicit user conversion.
- [ ] Writer paths covered by this issue do not mutate their input objects.
- [ ] Regression tests demonstrate writer non-mutation, including relevant zero-copy/shared-data cases.
- [ ] Zero-copy/copy semantics used at the `Mesh`/`Ceco` boundary are explicitly tested.
- [ ] A minimal `MeshLike` protocol is added if, after implementation, it proves useful for documenting/type-checking the structural writer contract.
- [ ] Existing `Mesh` behaviour remains compatible.
- [ ] No new test failures are introduced relative to the recorded green baseline.
- [ ] The result remains a small compatibility seam, not a package-wide `Ceco` migration.

## Expected outcome

After this work, the architecture should have a clean seam approximately like:

```text
                         MeshLike
                     structural contract
                        /          \
                       /            \
                    Mesh            Ceco
                       \            /
                        \          /
                      shared operations
                             |
                   existing format writers
```

with the additional behavioural invariant:

```text
writer(input) -> output file

input state before == input state after
```

This should leave the project in a good position to pause for another architectural review before beginning a new feature spike such as VTKHDF support.
