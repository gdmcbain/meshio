import argparse

import numpy

from .._helpers import _writer_map, read, reader_map, write
from ._helpers import _get_version_text


def convert(argv=None):
    # Parse command line arguments.
    parser = _get_convert_parser()
    args = parser.parse_args(argv)

    # read mesh data
    mesh = read(args.infile, file_format=args.input_format)

    if args.prune:
        mesh.prune()

    if (
        args.prune_z_0
        and mesh.points.shape[1] == 3
        and numpy.all(numpy.abs(mesh.points[:, 2]) < 1.0e-13)
    ):
        mesh.points = mesh.points[:, :2]

    # Some converters (like VTK) require `points` to be contiguous.
    mesh.points = numpy.ascontiguousarray(mesh.points)

    if args.sets_to_int_data:
        mesh.sets_to_int_data()

    if args.int_data_to_sets:
        mesh.int_data_to_sets()

    # write it out
    kwargs = {"file_format": args.output_format}
    if args.float_format is not None:
        kwargs["float_fmt"] = args.float_format

    write(args.outfile, mesh, **kwargs)


def _get_convert_parser():
    parser = argparse.ArgumentParser(
        description=("Convert between mesh formats."),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("infile", type=str, help="mesh file to be read from")

    parser.add_argument(
        "--input-format",
        "-i",
        type=str,
        choices=list(reader_map.keys()),
        help="input file format",
        default=None,
    )

    parser.add_argument(
        "--output-format",
        "-o",
        type=str,
        choices=list(_writer_map.keys()),
        help="output file format",
        default=None,
    )

    parser.add_argument("outfile", type=str, help="mesh file to be written to")

    parser.add_argument(
        "--float-format",
        "-f",
        type=str,
        help="float format used in output ASCII files (default: .15e)",
    )

    parser.add_argument(
        "--prune",
        "-p",
        action="store_true",
        help="remove lower order cells, remove orphaned nodes",
    )

    parser.add_argument(
        "--prune-z-0",
        "-z",
        action="store_true",
        help="remove third (z) dimension if all points are 0",
    )

    parser.add_argument(
        "--sets-to-int-data",
        "-s",
        action="store_true",
        help="if possible, convert sets to integer data (useful if the output type does not support sets)",
    )

    parser.add_argument(
        "--int-data-to-sets",
        "-d",
        action="store_true",
        help="if possible, convert integer data to sets (useful if the output type does not support integer data)",
    )

    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=_get_version_text(),
        help="display version information",
    )
    return parser
