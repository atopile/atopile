# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from copy import deepcopy
from pathlib import Path

from faebryk.libs.exceptions import UserResourceException, accumulate
from faebryk.libs.kicad.fileformats_common import (
    C_kicad_footprint_file_header,
    C_kicad_pcb_file_header,
)
from faebryk.libs.kicad.fileformats_latest import (
    KICAD_PCB_VERSION,
    C_kicad_footprint_file,
    C_kicad_pcb_file,
)
from faebryk.libs.kicad.fileformats_v5 import C_kicad_footprint_file_v5
from faebryk.libs.kicad.fileformats_v6 import C_kicad_footprint_file_v6
from faebryk.libs.sexp.dataclass_sexp import DecodeError, loads
from faebryk.libs.util import try_relative_to

logger = logging.getLogger(__name__)

# Release dates for reference:
# KiCad 9.0.0 - February 19, 2025
# KiCad 8.0.0 - January 31, 2024
# KiCad 7.0.0 - March 1, 2023
# KiCad 6.0.0 - December 15, 2021
# KiCad 5.1.0 - May 22, 2019
# KiCad 5.0.0 - July 21, 2018

KICAD_VERSION_NAMES = {
    20241229: "KiCad 9.0",
    20240108: "KiCad 8.0",
}


def kicad_footprint_file(path: Path | str) -> C_kicad_footprint_file:
    if isinstance(path, Path):
        _path = str(try_relative_to(path.resolve()))
        content = path.read_text(encoding="utf-8")
    else:
        _path = "<direct string>"
        content = path

    # cache
    # custom because don't care about origin & need to deepcopy
    if not hasattr(_kicad_footprint_file, "cache"):
        _kicad_footprint_file.cache = dict[str, C_kicad_footprint_file]()
    if content in _kicad_footprint_file.cache:
        return deepcopy(_kicad_footprint_file.cache[content])

    fp = _kicad_footprint_file(content, origin=_path)

    # cache
    _kicad_footprint_file.cache[content] = fp

    return deepcopy(fp)


def _kicad_footprint_file(
    path: str, origin: str | None = None
) -> C_kicad_footprint_file:
    acc = accumulate(DecodeError, group_message="No decoders succeeded")
    if path.startswith("(module"):
        with acc.collect():
            return loads(path, C_kicad_footprint_file_v5).convert_to_new()
    else:
        header = loads(path, C_kicad_footprint_file_header)
        version = header.footprint.version
        if version < 20240101:
            with acc.collect():
                return loads(path, C_kicad_footprint_file_v6).convert_to_new()
        else:
            with acc.collect():
                return loads(path, C_kicad_footprint_file)

            with acc.collect():
                return loads(path, C_kicad_footprint_file, ignore_assertions=True)

    # Nothing succeeded in loading the file
    raise UserResourceException(
        f"Not a valid KiCad footprint file: origin={origin}",
        markdown=False,
    ) from acc.get_exception()


def try_load_kicad_pcb_file(path: Path) -> C_kicad_pcb_file:
    """
    Attempt to load a KiCad PCB file.

    Raises an exception if the file is invalid, or not the current supported version.
    """

    logger.info("Loading KiCad PCB file: %s", path)

    try:
        return loads(path, C_kicad_pcb_file)
    except DecodeError as e:
        logger.info(str(e), exc_info=e)

        try:
            logger.info("Loading KiCad PCB file (header): %s", path)
            pcb = loads(path, C_kicad_pcb_file_header)
        except Exception:
            raise e

        if pcb.kicad_pcb.version != KICAD_PCB_VERSION:
            # TODO: link to kicad docs for file migration
            raise UserResourceException(
                f"Error loading KiCad PCB file {path}\n"
                f"Unsupported version: {pcb.kicad_pcb.version} "
                f"({KICAD_VERSION_NAMES[pcb.kicad_pcb.version]})\n"
                f"Expected: {KICAD_PCB_VERSION} "
                f"({KICAD_VERSION_NAMES[KICAD_PCB_VERSION]})\n"
                f"Manually open the kicad file in "
                f"({KICAD_VERSION_NAMES[KICAD_PCB_VERSION]}) and save it.",
                markdown=False,
            )

        raise e
