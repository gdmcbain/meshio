"""Guard against NumPy-scalar repr leaking into ASCII output (issue #1).

These are writer-only checks, independent of our own readers: they assert that
serialized text contains bare numbers, not tokens such as ``np.float64(0.0)``
produced by applying ``repr`` to a NumPy scalar under NumPy 2.x.
"""

import numpy as np

import meshio

from . import helpers

_FORBIDDEN = [b"np.float", b"np.int", b"np.uint", b"np.str"]


def _assert_bare(data: bytes):
    for token in _FORBIDDEN:
        assert token not in data, f"{token!r} leaked into ASCII output"


def test_gmsh_ascii_point_data_bare(tmp_path):
    mesh = helpers.add_point_data(helpers.tri_mesh, 1)
    p = tmp_path / "m.msh"
    meshio.gmsh.write(p, mesh, binary=False)
    _assert_bare(p.read_bytes())


def test_ugrid_ascii_points_bare(tmp_path):
    p = tmp_path / "m.ugrid"
    meshio.ugrid.write(p, helpers.tri_mesh)
    _assert_bare(p.read_bytes())


def test_dolfin_cell_data_bare(tmp_path):
    mesh = helpers.add_cell_data(helpers.tri_mesh, [("a", (), np.int32)])
    p = tmp_path / "m.xml"
    meshio.dolfin.write(p, mesh)
    # cell data is written to a sibling file m_a.xml
    data = b"".join(f.read_bytes() for f in tmp_path.glob("*.xml"))
    _assert_bare(data)
