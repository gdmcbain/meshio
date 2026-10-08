import numpy as np
import pytest

import meshio

from . import helpers


def test_construct_points_cells():
    ceco = meshio.Ceco(helpers.tri_mesh.points, helpers.tri_mesh.cells)
    assert len(ceco.points) == len(helpers.tri_mesh.points)
    assert [c.type for c in ceco.cells] == [c.type for c in helpers.tri_mesh.cells]


def test_not_a_mesh_subclass():
    ceco = meshio.Ceco(helpers.tri_mesh.points, helpers.tri_mesh.cells)
    assert not isinstance(ceco, meshio.Mesh)
    assert not issubclass(meshio.Ceco, meshio.Mesh)


def test_from_meshio_shares_arrays():
    mesh = helpers.tri_mesh
    ceco = meshio.Ceco.from_meshio(mesh)
    assert np.shares_memory(ceco.points, mesh.points)
    for cb_ceco, cb_mesh in zip(ceco.cells, mesh.cells):
        assert np.shares_memory(cb_ceco.data, cb_mesh.data)


def test_from_meshio_copy_is_independent():
    mesh = helpers.tri_mesh.copy()
    ceco = meshio.Ceco.from_meshio(mesh, copy=True)
    assert not np.shares_memory(ceco.points, mesh.points)
    ceco.points[0, 0] += 1.0
    assert mesh.points[0, 0] != ceco.points[0, 0]


def test_shared_points_alias():
    # zero-copy sharing is deliberate: mutating the Ceco is visible via the source
    mesh = helpers.tri_mesh.copy()
    ceco = meshio.Ceco.from_meshio(mesh)
    ceco.points[0, 0] += 1.0
    assert mesh.points[0, 0] == ceco.points[0, 0]


def test_mesh_api_preserved():
    mesh = meshio.Mesh(helpers.tri_mesh.points, helpers.tri_mesh.cells)
    assert not isinstance(mesh, meshio.Ceco)
    assert mesh.get_cells_type("triangle").shape[1] == 3


def test_delegated_methods_match_mesh():
    mesh = helpers.tri_mesh.copy()
    ceco = meshio.Ceco.from_meshio(mesh.copy())
    assert np.array_equal(
        ceco.get_cells_type("triangle"), mesh.get_cells_type("triangle")
    )
    assert "triangle" in ceco.cells_dict


def test_point_sets_to_data_delegation():
    ceco = meshio.Ceco(
        helpers.tri_mesh.points,
        helpers.tri_mesh.cells,
        point_sets={"a": np.array([0, 1]), "b": np.array([2, 3])},
    )
    assert ceco.point_sets
    ceco.point_sets_to_data()
    assert not ceco.point_sets
    assert "a-b" in ceco.point_data


@pytest.mark.parametrize(
    "extension, file_format, reader",
    [
        (".vtu", None, meshio.vtu.read),
        # .msh is shared by several formats, so name the writer explicitly
        (".msh", "gmsh", meshio.gmsh.read),
        (".stl", None, meshio.stl.read),
    ],
)
def test_delegated_write(extension, file_format, reader, tmp_path):
    # Round trip through our own writer and reader: this checks that ceco.write
    # delegates and that information is preserved. It is NOT a format-conformance
    # test (see doc/plans/CECOIO-TESTING-PRINCIPLES.md, principles 1 and 4).
    # copy=True so the shared-array hazard does not perturb the module-level fixture.
    ceco = meshio.Ceco.from_meshio(helpers.tri_mesh, copy=True)

    def writer(p, mesh):
        mesh.write(p, file_format=file_format)

    helpers.write_read(tmp_path, writer, reader, ceco, 1.0e-12, extension=extension)


# --- shared-operation parity (seam between Mesh and Ceco via _meshlike) ---


def _rich_mesh_kwargs():
    # one triangle block (2 cells); every point and cell belongs to exactly one set
    return dict(
        points=np.array(
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]]
        ),
        cells=[("triangle", np.array([[0, 1, 2], [0, 2, 3]]))],
        point_data={"temp": np.array([1.0, 2.0, 3.0, 4.0])},
        cell_data={"mat": [np.array([10, 20])]},
        point_sets={"left": np.array([0, 3]), "right": np.array([1, 2])},
        cell_sets={"a": [np.array([0])], "b": [np.array([1])]},
    )


def test_shared_ops_match_mesh():
    kwargs = _rich_mesh_kwargs()
    mesh = meshio.Mesh(**kwargs)
    ceco = meshio.Ceco(**kwargs)

    assert np.array_equal(
        ceco.get_cells_type("triangle"), mesh.get_cells_type("triangle")
    )
    assert np.array_equal(
        ceco.get_cell_data("mat", "triangle"), mesh.get_cell_data("mat", "triangle")
    )
    assert ceco.cells_dict.keys() == mesh.cells_dict.keys()
    assert np.array_equal(ceco.cells_dict["triangle"], mesh.cells_dict["triangle"])
    assert np.array_equal(
        ceco.cell_data_dict["mat"]["triangle"],
        mesh.cell_data_dict["mat"]["triangle"],
    )
    assert ceco.cell_sets_dict.keys() == mesh.cell_sets_dict.keys()


def test_ceco_not_backed_by_mesh():
    # Ceco must not reach into Mesh implementation to build itself.
    ceco = meshio.Ceco(**_rich_mesh_kwargs())
    assert not isinstance(ceco, meshio.Mesh)


def test_pure_sets_to_data_do_not_mutate():
    from meshio import _meshlike

    ceco = meshio.Ceco(**_rich_mesh_kwargs())
    name, intfun = _meshlike.point_sets_to_data(ceco)
    assert name == "left-right"
    # the pure helper returns derived data and leaves the object untouched
    assert ceco.point_sets
    assert "left-right" not in ceco.point_data

    name, intfun = _meshlike.cell_sets_to_data(ceco)
    assert name == "a-b"
    assert ceco.cell_sets
    assert "a-b" not in ceco.cell_data


# --- writer non-mutation regression (writers observe, never mutate, input) ---


def _snapshot(m):
    return dict(
        points=m.points.copy(),
        cell_types=[cb.type for cb in m.cells],
        cell_data_arrays=[cb.data.copy() for cb in m.cells],
        point_data={k: v.copy() for k, v in m.point_data.items()},
        cell_data={k: [a.copy() for a in v] for k, v in m.cell_data.items()},
        field_data={k: v.copy() for k, v in m.field_data.items()},
        point_sets={k: v.copy() for k, v in m.point_sets.items()},
        cell_sets={k: list(v) for k, v in m.cell_sets.items()},
    )


def _assert_unchanged(m, snap):
    assert np.array_equal(m.points, snap["points"])
    assert [cb.type for cb in m.cells] == snap["cell_types"]
    for cb, data in zip(m.cells, snap["cell_data_arrays"]):
        assert np.array_equal(cb.data, data)
    assert m.point_data.keys() == snap["point_data"].keys()
    for k in snap["point_data"]:
        assert np.array_equal(m.point_data[k], snap["point_data"][k])
    assert m.cell_data.keys() == snap["cell_data"].keys()
    for k in snap["cell_data"]:
        for a, b in zip(m.cell_data[k], snap["cell_data"][k]):
            assert np.array_equal(a, b)
    assert m.point_sets.keys() == snap["point_sets"].keys()
    for k in snap["point_sets"]:
        assert np.array_equal(m.point_sets[k], snap["point_sets"][k])
    assert m.cell_sets.keys() == snap["cell_sets"].keys()


@pytest.mark.parametrize(
    "writer",
    [
        lambda p, m: m.write(p, file_format="vtu"),
        lambda p, m: meshio.vtk.write(p, m, fmt_version="5.1"),
        lambda p, m: meshio.vtk.write(p, m, fmt_version="4.2"),
    ],
)
def test_writer_does_not_mutate_mesh(writer, tmp_path):
    mesh = meshio.Mesh(**_rich_mesh_kwargs())
    snap = _snapshot(mesh)
    writer(tmp_path / "out", mesh)
    _assert_unchanged(mesh, snap)


def test_ply_writer_does_not_mutate_mesh(tmp_path):
    # PLY casts int64 connectivity down to int32; that must not alter the input.
    mesh = meshio.Mesh(
        np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0]]),
        [("triangle", np.array([[0, 1, 2]], dtype=np.int64))],
    )
    snap = _snapshot(mesh)
    mesh.write(tmp_path / "out.ply")
    _assert_unchanged(mesh, snap)
    assert mesh.cells[0].data.dtype == np.int64


def test_zero_copy_write_does_not_mutate_source(tmp_path):
    # from_meshio(copy=False) deliberately shares arrays with the source Mesh;
    # writing the Ceco must not reach back and mutate that source.
    mesh = meshio.Mesh(**_rich_mesh_kwargs())
    snap = _snapshot(mesh)
    ceco = meshio.Ceco.from_meshio(mesh, copy=False)
    ceco.write(tmp_path / "out.vtu")
    _assert_unchanged(mesh, snap)


def test_writer_order_independence(tmp_path):
    # Writing in either order must give identical bytes, i.e. the first write did
    # not change the shared object seen by the second.
    m1 = meshio.Mesh(**_rich_mesh_kwargs())
    m1.write(tmp_path / "a.vtu")
    first_vtu = (tmp_path / "a.vtu").read_bytes()

    m2 = meshio.Mesh(**_rich_mesh_kwargs())
    m2.write(tmp_path / "b.msh", file_format="gmsh")
    m2.write(tmp_path / "b.vtu")
    second_vtu = (tmp_path / "b.vtu").read_bytes()

    assert first_vtu == second_vtu
