from __future__ import annotations

import copy

import numpy as np
from numpy.typing import ArrayLike

from . import _meshlike
from ._common import warn

topological_dimension = {
    "line": 1,
    "polygon": 2,
    "triangle": 2,
    "quad": 2,
    "tetra": 3,
    "hexahedron": 3,
    "wedge": 3,
    "pyramid": 3,
    "line3": 1,
    "triangle6": 2,
    "quad9": 2,
    "tetra10": 3,
    "hexahedron27": 3,
    "wedge18": 3,
    "pyramid14": 3,
    "vertex": 0,
    "quad8": 2,
    "hexahedron20": 3,
    "triangle10": 2,
    "triangle15": 2,
    "triangle21": 2,
    "line4": 1,
    "line5": 1,
    "line6": 1,
    "tetra20": 3,
    "tetra35": 3,
    "tetra56": 3,
    "quad16": 2,
    "quad25": 2,
    "quad36": 2,
    "triangle28": 2,
    "triangle36": 2,
    "triangle45": 2,
    "triangle55": 2,
    "triangle66": 2,
    "quad49": 2,
    "quad64": 2,
    "quad81": 2,
    "quad100": 2,
    "quad121": 2,
    "line7": 1,
    "line8": 1,
    "line9": 1,
    "line10": 1,
    "line11": 1,
    "tetra84": 3,
    "tetra120": 3,
    "tetra165": 3,
    "tetra220": 3,
    "tetra286": 3,
    "wedge40": 3,
    "wedge75": 3,
    "hexahedron64": 3,
    "hexahedron125": 3,
    "hexahedron216": 3,
    "hexahedron343": 3,
    "hexahedron512": 3,
    "hexahedron729": 3,
    "hexahedron1000": 3,
    "wedge126": 3,
    "wedge196": 3,
    "wedge288": 3,
    "wedge405": 3,
    "wedge550": 3,
    "VTK_LAGRANGE_CURVE": 1,
    "VTK_LAGRANGE_TRIANGLE": 2,
    "VTK_LAGRANGE_QUADRILATERAL": 2,
    "VTK_LAGRANGE_TETRAHEDRON": 3,
    "VTK_LAGRANGE_HEXAHEDRON": 3,
    "VTK_LAGRANGE_WEDGE": 3,
    "VTK_LAGRANGE_PYRAMID": 3,
}


class CellBlock:
    def __init__(
        self,
        cell_type: str,
        data: list | np.ndarray,
        tags: list[str] | None = None,
    ):
        self.type = cell_type
        self.data = data

        if cell_type.startswith("polyhedron"):
            self.dim = 3
        else:
            self.data = np.asarray(self.data)
            self.dim = topological_dimension[cell_type]

        self.tags = [] if tags is None else tags

    def __repr__(self):
        items = [
            "meshio CellBlock",
            f"type: {self.type}",
            f"num cells: {len(self.data)}",
            f"tags: {self.tags}",
        ]
        return "<" + ", ".join(items) + ">"

    def __len__(self):
        return len(self.data)


class Mesh:
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
        lines = ["<meshio mesh object>", f"  Number of points: {len(self.points)}"]
        special_cells = [
            "polygon",
            "polyhedron",
            "VTK_LAGRANGE_CURVE",
            "VTK_LAGRANGE_TRIANGLE",
            "VTK_LAGRANGE_QUADRILATERAL",
            "VTK_LAGRANGE_TETRAHEDRON",
            "VTK_LAGRANGE_HEXAHEDRON",
            "VTK_LAGRANGE_WEDGE",
            "VTK_LAGRANGE_PYRAMID",
        ]
        if len(self.cells) > 0:
            lines.append("  Number of cells:")
            for cell_block in self.cells:
                string = cell_block.type
                if cell_block.type in special_cells:
                    string += f"({cell_block.data.shape[1]})"
                lines.append(f"    {string}: {len(cell_block)}")
        else:
            lines.append("  No cells.")

        if self.point_sets:
            names = ", ".join(self.point_sets.keys())
            lines.append(f"  Point sets: {names}")

        if self.cell_sets:
            names = ", ".join(self.cell_sets.keys())
            lines.append(f"  Cell sets: {names}")

        if self.point_data:
            names = ", ".join(self.point_data.keys())
            lines.append(f"  Point data: {names}")

        if self.cell_data:
            names = ", ".join(self.cell_data.keys())
            lines.append(f"  Cell data: {names}")

        if self.field_data:
            names = ", ".join(self.field_data.keys())
            lines.append(f"  Field data: {names}")

        return "\n".join(lines)

    def copy(self):
        return copy.deepcopy(self)

    def write(self, path_or_buf, file_format: str | None = None, **kwargs):
        # avoid circular import
        from ._helpers import write

        write(path_or_buf, self, file_format, **kwargs)

    def get_cells_type(self, cell_type: str):
        return _meshlike.get_cells_type(self, cell_type)

    def get_cell_data(self, name: str, cell_type: str):
        return _meshlike.get_cell_data(self, name, cell_type)

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
    def read(cls, path_or_buf, file_format=None):
        # avoid circular import
        from ._helpers import read

        # 2021-02-21
        warn("meshio.Mesh.read is deprecated, use meshio.read instead")
        return read(path_or_buf, file_format)

    def cell_sets_to_data(self, data_name: str | None = None):
        # If possible, convert cell sets to integer cell data. This is possible if all
        # cells appear exactly in one group.
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

    # This used to be int_data_to_sets(), converting _all_ cell and point data.
    # This is not useful in many cases, as one usually only wants one
    # particular data array (e.g., "MaterialIDs") converted to sets.
    def cell_data_to_sets(self, key: str):
        """Convert point_data to cell_sets."""
        data = self.cell_data[key]

        # handle all int and uint data
        if not all(v.dtype.kind in ["i", "u"] for v in data):
            raise RuntimeError(f"cell_data['{key}'] is not int data.")

        tags = np.unique(np.concatenate(data))

        # try and get the names by splitting the key along "-" (this is how
        # sets_to_int_data() forms the key)
        names = key.split("-")
        # remove duplicates and preserve order
        # <https://stackoverflow.com/a/7961390/353337>:
        names = list(dict.fromkeys(names))
        if len(names) != len(tags):
            # alternative names
            names = [f"set-{key}-{tag}" for tag in tags]

        # TODO there's probably a better way besides np.where, something from
        # np.unique or np.sort
        for name, tag in zip(names, tags):
            self.cell_sets[name] = [np.where(d == tag)[0] for d in data]

        # remove the cell data
        del self.cell_data[key]

    def point_data_to_sets(self, key: str):
        """Convert point_data to point_sets."""
        data = self.point_data[key]

        # handle all int and uint data
        if not all(v.dtype.kind in ["i", "u"] for v in data):
            raise RuntimeError(f"point_data['{key}'] is not int data.")

        tags = np.unique(data)

        # try and get the names by splitting the key along "-" (this is how
        # sets_to_int_data() forms the key
        names = key.split("-")
        # remove duplicates and preserve order
        # <https://stackoverflow.com/a/7961390/353337>:
        names = list(dict.fromkeys(names))
        if len(names) != len(tags):
            # alternative names
            names = [f"set-key-{tag}" for tag in tags]

        # TODO there's probably a better way besides np.where, something from
        # np.unique or np.sort
        for name, tag in zip(names, tags):
            self.point_sets[name] = np.where(data == tag)[0]

        # remove the cell data
        del self.point_data[key]
