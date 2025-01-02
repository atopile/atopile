# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

from faebryk.libs.exceptions import UserResourceException, accumulate
from faebryk.libs.kicad.fileformats import C_kicad_footprint_file
from faebryk.libs.kicad.fileformats_common import C_kicad_footprint_file_header
from faebryk.libs.kicad.fileformats_v5 import C_kicad_footprint_file_v5
from faebryk.libs.kicad.fileformats_v6 import C_kicad_footprint_file_v6
from faebryk.libs.sexp.dataclass_sexp import DecodeError, loads
from faebryk.libs.util import try_relative_to

logger = logging.getLogger(__name__)


def kicad_footprint_file(path: Path) -> C_kicad_footprint_file:
    acc = accumulate(DecodeError, group_message="No decoders succeeded")
    if path.read_text().startswith("(module"):
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
        f"Footprint {try_relative_to(path.resolve())} is not"
        " a valid KiCad footprint file",
        markdown=False,
    ) from acc.get_exception()
