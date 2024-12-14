# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

from faebryk.libs.exceptions import UserResourceException
from faebryk.libs.kicad.fileformats import C_kicad_footprint_file
from faebryk.libs.kicad.fileformats_v5 import C_kicad_footprint_file_v5
from faebryk.libs.sexp.dataclass_sexp import DecodeError

logger = logging.getLogger(__name__)


def kicad_footprint_file(path: Path) -> C_kicad_footprint_file:
    try:
        if path.read_text().startswith("(module"):
            return C_kicad_footprint_file_v5.loads(path).convert_to_new()

        return C_kicad_footprint_file.loads(path)
    except DecodeError as ex:
        raise UserResourceException(
            f'Footprint "{path.name}" is not a valid KiCad footprint file'
        ) from ex
