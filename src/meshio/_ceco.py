from __future__ import annotations

import copy

from numpy.typing import ArrayLike

from . import _meshlike
from ._mesh import CellBlock, Mesh


class Ceco:
    """Neutral cell-complex representation (CEll COmplex).

    Independent of ``meshio.Mesh`` (not a subclass). For the ordinary
    points-plus-cells case it shares Mesh's data vocabulary and the shared
    operations in :mod:`meshio._meshlike`; no Mesh instance backs a Ceco.
    """

    def __init__(
        self,
        points: ArrayLike,
        cells: dict[str, ArrayLike] | list[tuple[str, ArrayLike] | CellBlock],
        point_data: dict[str, ArrayLike] | None = None,
        cell_data: dict[str, list[ArrayLike]] | None = None,
        field_data=None,
        point_sets: dict[str, ArrayLike] | None = None,
        cell_sets: dict[str, list[ArrayLike]] | None = None,
        gmsh_periodic=None,
        info=None,
    ):
        _meshlike.init_mesh_like(
            self,
            points,
            cells,
            point_data,
            cell_data,
            field_data,
            point_sets,
            cell_sets,
            gmsh_periodic,
            info,
        )

    def __repr__(self):
        lines = ["<ceco object>", f"  Number of points: {len(self.points)}"]
        if len(self.cells) > 0:
            lines.append("  Number of cells:")
            for cell_block in self.cells:
                lines.append(f"    {cell_block.type}: {len(cell_block)}")
        else:
            lines.append("  No cells.")
        for label, attr in [
            ("Point sets", self.point_sets),
            ("Cell sets", self.cell_sets),
            ("Point data", self.point_data),
            ("Cell data", self.cell_data),
            ("Field data", self.field_data),
        ]:
            if attr:
                lines.append(f"  {label}: {', '.join(attr.keys())}")
        return "\n".join(lines)

    def copy(self):
        return copy.deepcopy(self)

    def write(self, path_or_buf, file_format: str | None = None, **kwargs):
        # avoid circular import
        from ._helpers import write

        write(path_or_buf, self, file_format, **kwargs)

    # Operations below reuse the shared _meshlike implementations applied to this
    # object's own attributes, keeping behaviour identical without inheritance.

    def get_cells_type(self, cell_type: str):
        return _meshlike.get_cells_type(self, cell_type)

    def get_cell_data(self, name: str, cell_type: str):
        return _meshlike.get_cell_data(self, name, cell_type)

    def cell_sets_to_data(self, data_name: str | None = None):
        result = _meshlike.cell_sets_to_data(self, data_name)
        if result is not None:
            data_name, intfun = result
            self.cell_data[data_name] = intfun
            self.cell_sets = {}

    def point_sets_to_data(self, join_char: str = "-") -> None:
        result = _meshlike.point_sets_to_data(self, join_char)
        if result is not None:
            data_name, intfun = result
            self.point_data[data_name] = intfun
            self.point_sets = {}

    @property
    def cells_dict(self):
        return _meshlike.cells_dict(self)

    @property
    def cell_data_dict(self):
        return _meshlike.cell_data_dict(self)

    @property
    def cell_sets_dict(self):
        return _meshlike.cell_sets_dict(self)

    @classmethod
    def from_meshio(cls, mesh: Mesh, copy: bool = False) -> Ceco:
        """Create a Ceco from a ``meshio.Mesh``.

        Arrays are shared with ``mesh`` by default (zero-copy); pass
        ``copy=True`` for independent arrays.
        """
        if copy:
            mesh = mesh.copy()
        return cls(
            mesh.points,
            mesh.cells,
            point_data=mesh.point_data,
            cell_data=mesh.cell_data,
            field_data=mesh.field_data,
            point_sets=mesh.point_sets,
            cell_sets=mesh.cell_sets,
            gmsh_periodic=mesh.gmsh_periodic,
            info=mesh.info,
        )
