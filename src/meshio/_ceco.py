from __future__ import annotations

import copy

from numpy.typing import ArrayLike

from ._mesh import CellBlock, Mesh


class Ceco:
    """Neutral cell-complex representation (CEll COmplex).

    Independent of ``meshio.Mesh`` (not a subclass). For the ordinary
    points-plus-cells case it shares Mesh's data vocabulary and reuses Mesh
    operations by internal delegation; no Mesh instance backs a Ceco.
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
        # Reuse Mesh's construction and validation to populate this object's own
        # attributes; this stores no Mesh instance.
        Mesh.__init__(
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

    # Operations below reuse Mesh's implementations applied to this object's own
    # attributes (duck typing), keeping behaviour identical without inheritance.

    def get_cells_type(self, cell_type: str):
        return Mesh.get_cells_type(self, cell_type)

    def get_cell_data(self, name: str, cell_type: str):
        return Mesh.get_cell_data(self, name, cell_type)

    def cell_sets_to_data(self, data_name: str | None = None):
        return Mesh.cell_sets_to_data(self, data_name)

    def point_sets_to_data(self, join_char: str = "-") -> None:
        return Mesh.point_sets_to_data(self, join_char)

    @property
    def cells_dict(self):
        return Mesh.cells_dict.fget(self)

    @property
    def cell_data_dict(self):
        return Mesh.cell_data_dict.fget(self)

    @property
    def cell_sets_dict(self):
        return Mesh.cell_sets_dict.fget(self)

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
