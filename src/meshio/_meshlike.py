"""Shared operations and structural contract for mesh-like objects.

These pure functions operate on the attribute surface (``points``, ``cells``,
``cell_data``, ``point_sets``, ``cell_sets`` ...) common to :class:`meshio.Mesh`
and :class:`meshio.Ceco`, so neither class needs to depend on the other's
implementation. The ``*_to_data`` helpers here are non-mutating: they return the
derived data instead of writing it back onto the object.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import ArrayLike

from ._common import num_nodes_per_cell, warn


def init_mesh_like(
    obj,
    points: ArrayLike,
    cells,
    point_data=None,
    cell_data=None,
    field_data=None,
    point_sets=None,
    cell_sets=None,
    gmsh_periodic=None,
    info=None,
) -> None:
    """Populate ``obj`` with normalized, validated mesh attributes.

    Shared constructor body for ``Mesh`` and ``Ceco``; imported locally to avoid
    a circular import with :mod:`meshio._mesh`.
    """
    from ._mesh import CellBlock

    obj.points = np.asarray(points)
    if isinstance(cells, dict):
        # old dict form, deprecated; convert to list of tuples
        cells = list(cells.items())

    obj.cells = []
    for cell_block in cells:
        if isinstance(cell_block, tuple):
            cell_type, data = cell_block
            cell_block = CellBlock(
                cell_type,
                # polyhedron data cannot be converted to numpy arrays
                # because the sublists don't all have the same length
                data if cell_type.startswith("polyhedron") else np.asarray(data),
            )
        obj.cells.append(cell_block)

    obj.point_data = {} if point_data is None else point_data
    obj.cell_data = {} if cell_data is None else cell_data
    obj.field_data = {} if field_data is None else field_data
    obj.point_sets = {} if point_sets is None else point_sets
    obj.cell_sets = {} if cell_sets is None else cell_sets
    obj.gmsh_periodic = gmsh_periodic
    obj.info = info

    # assert point data consistency and convert to numpy arrays
    for key, item in obj.point_data.items():
        obj.point_data[key] = np.asarray(item)
        if len(obj.point_data[key]) != len(obj.points):
            raise ValueError(
                f"len(points) = {len(obj.points)}, "
                f'but len(point_data["{key}"]) = {len(obj.point_data[key])}'
            )

    # assert cell data consistency and convert to numpy arrays
    for key, data in obj.cell_data.items():
        if len(data) != len(cells):
            raise ValueError(
                f"Incompatible cell data '{key}'. "
                f"{len(cells)} cell blocks, but '{key}' has {len(data)} blocks."
            )

        for k in range(len(data)):
            data[k] = np.asarray(data[k])
            if len(data[k]) != len(obj.cells[k]):
                raise ValueError(
                    "Incompatible cell data. "
                    + f"Cell block {k} ('{obj.cells[k].type}') "
                    + f"has length {len(obj.cells[k])}, but "
                    + f"corresponding cell data item has length {len(data[k])}."
                )


def get_cells_type(obj, cell_type: str):
    if not any(c.type == cell_type for c in obj.cells):
        return np.empty((0, num_nodes_per_cell[cell_type]), dtype=int)
    return np.concatenate([c.data for c in obj.cells if c.type == cell_type])


def get_cell_data(obj, name: str, cell_type: str):
    return np.concatenate(
        [d for c, d in zip(obj.cells, obj.cell_data[name]) if c.type == cell_type]
    )


def cells_dict(obj):
    cells_dict = {}
    for cell_block in obj.cells:
        if cell_block.type not in cells_dict:
            cells_dict[cell_block.type] = []
        cells_dict[cell_block.type].append(cell_block.data)
    # concatenate
    for key, value in cells_dict.items():
        cells_dict[key] = np.concatenate(value)
    return cells_dict


def cell_data_dict(obj):
    cell_data_dict = {}
    for key, value_list in obj.cell_data.items():
        cell_data_dict[key] = {}
        for value, cell_block in zip(value_list, obj.cells):
            if cell_block.type not in cell_data_dict[key]:
                cell_data_dict[key][cell_block.type] = []
            cell_data_dict[key][cell_block.type].append(value)

        for cell_type, val in cell_data_dict[key].items():
            cell_data_dict[key][cell_type] = np.concatenate(val)
    return cell_data_dict


def cell_sets_dict(obj):
    sets_dict = {}
    for key, member_list in obj.cell_sets.items():
        sets_dict[key] = {}
        offsets = {}
        for members, cells in zip(member_list, obj.cells):
            if members is None:
                continue
            if cells.type in offsets:
                offset = offsets[cells.type]
                offsets[cells.type] += cells.data.shape[0]
            else:
                offset = 0
                offsets[cells.type] = cells.data.shape[0]
            if cells.type in sets_dict[key]:
                sets_dict[key][cells.type].append(members + offset)
            else:
                sets_dict[key][cells.type] = [members + offset]
    return {
        key: {
            cell_type: np.concatenate(members)
            for cell_type, members in sets.items()
            if sum(map(np.size, members))
        }
        for key, sets in sets_dict.items()
    }


def point_sets_to_data(obj, join_char: str = "-"):
    """Derive integer point data from ``obj.point_sets`` without mutating ``obj``.

    Returns ``(data_name, intfun)`` or ``None`` when there are no point sets.
    """
    default_value = -1
    if len(obj.point_sets) == 0:
        return None
    intfun = np.full(len(obj.points), default_value, dtype=int)
    for i, cc in enumerate(obj.point_sets.values()):
        intfun[cc] = i

    if np.any(intfun == default_value):
        warn(
            "Not all points are part of a point set. "
            f"Using default value {default_value}."
        )

    data_name = join_char.join(obj.point_sets.keys())
    return data_name, intfun


def cell_sets_to_data(obj, data_name: str | None = None):
    """Derive integer cell data from ``obj.cell_sets`` without mutating ``obj``.

    Returns ``(data_name, intfun)`` or ``None`` when there are no cell sets.
    Possible only if every cell appears in exactly one group.
    """
    default_value = -1
    if len(obj.cell_sets) == 0:
        return None
    intfun = []
    for k, c in enumerate(zip(*obj.cell_sets.values())):
        # Go for -1 as the default value. (NaN is not int.)
        arr = np.full(len(obj.cells[k]), default_value, dtype=int)
        for i, cc in enumerate(c):
            if cc is None:
                continue
            arr[cc] = i
        intfun.append(arr)

    for item in intfun:
        num_default = np.sum(item == default_value)
        if num_default > 0:
            warn(
                f"{num_default} cells are not part of any cell set. "
                f"Using default value {default_value}."
            )
            break

    if data_name is None:
        data_name = "-".join(obj.cell_sets.keys())
    return data_name, intfun


@runtime_checkable
class MeshLike(Protocol):
    """Structural contract required by existing writers.

    Derived from the attributes and methods writers actually touch, not from any
    future ``Ceco`` capability. Both ``Mesh`` and ``Ceco`` satisfy it.
    """

    points: np.ndarray
    cells: list
    point_data: dict
    cell_data: dict
    field_data: dict
    point_sets: dict
    cell_sets: dict
    gmsh_periodic: object
    info: object

    def get_cells_type(self, cell_type: str): ...

    def get_cell_data(self, name: str, cell_type: str): ...

    def point_sets_to_data(self, join_char: str = "-") -> None: ...

    def cell_sets_to_data(self, data_name: str | None = None): ...

    @property
    def cells_dict(self): ...

    @property
    def cell_data_dict(self): ...

    @property
    def cell_sets_dict(self): ...
