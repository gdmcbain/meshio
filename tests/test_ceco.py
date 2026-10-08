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
