# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
from pathlib import Path
from typing import Sequence

from atopile.config import config
from faebryk.libs.exceptions import (
    UserResourceException,
    accumulate,
)
from faebryk.libs.kicad.fileformats import C_footprint, C_kicad_fp_lib_table_file
from faebryk.libs.kicad.fileformats_version import kicad_footprint_file
from faebryk.libs.kicad.paths import GLOBAL_FP_DIR_PATH, GLOBAL_FP_LIB_PATH
from faebryk.libs.util import KeyErrorNotFound, find

logger = logging.getLogger(__name__)

# TODO: dynamic spacing based on footprint dimensions?
HORIZONTAL_SPACING = 10
VERTICAL_SPACING = -5  # negative is upwards

NO_LCSC_DISPLAY = "No LCSC number"


class LibNotInTable(Exception):
    def __init__(self, *args: object, lib_id: str, lib_table_path: Path) -> None:
        super().__init__(*args)
        self.lib_id = lib_id
        self.lib_table_path = lib_table_path


def _find_footprint(
    lib_tables: Sequence[os.PathLike], lib_id: str
) -> C_kicad_fp_lib_table_file.C_fp_lib_table.C_lib:
    lib_tables = [Path(lib_table) for lib_table in lib_tables]

    err_accumulator = accumulate(LibNotInTable, FileNotFoundError)

    for lib_table_path in lib_tables:
        with err_accumulator.collect():
            lib_table = C_kicad_fp_lib_table_file.loads(lib_table_path)
            try:
                return find(lib_table.fp_lib_table.libs, lambda x: x.name == lib_id)
            except KeyErrorNotFound as ex:
                raise LibNotInTable(
                    lib_id=lib_id, lib_table_path=lib_table_path
                ) from ex

    if ex := err_accumulator.get_exception():
        raise ex

    raise ValueError("No footprint libraries provided")


def get_footprint(identifier: str, fp_lib_path: Path) -> C_footprint:
    lib_id, fp_name = identifier.split(":")
    lib = _find_footprint([fp_lib_path, GLOBAL_FP_LIB_PATH], lib_id)
    dir_path = Path(
        (lib.uri)
        .replace("${KIPRJMOD}", str(config.build.paths.fp_lib_table.parent))
        .replace("${KICAD8_FOOTPRINT_DIR}", str(GLOBAL_FP_DIR_PATH))
    )

    path = dir_path / f"{fp_name}.kicad_mod"
    try:
        return kicad_footprint_file(path).footprint
    except FileNotFoundError as ex:
        raise UserResourceException(
            f"Footprint `{fp_name}` doesn't exist in library `{lib_id}`"
        ) from ex
