# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

import faebryk.core.node as fabll
from faebryk.core.solver.solver import Solver

logger = logging.getLogger(__name__)


def export_parameters_to_file(
    module: fabll.Node, solver: Solver, path: Path, build_id: str | None = None
):
    """
    Export the variables of the given module to file(s).

    Args:
        module: The application root node
        solver: The solver used for parameter resolution
        path: Output file path
        build_id: Build ID from server (links to build history)
    """
    from faebryk.exporters.parameters.json_parameters import write_variables_to_file

    logger.info(f"Writing JSON variables to {path}")
    write_variables_to_file(
        module, solver, path, build_id=build_id, formats=("json", "markdown", "txt")
    )
