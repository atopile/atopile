# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""Surviving types from the old easyeda_types module.

Only types genuinely used beyond the parse-convert boundary live here:
enums (used by builders and tests) and Ee3dModelInfo (used by lcsc.py
for lazy 3D model loading).
"""

from dataclasses import dataclass
from enum import Enum


class EePadShape(str, Enum):
    ELLIPSE = "ELLIPSE"
    RECT = "RECT"
    OVAL = "OVAL"
    POLYGON = "POLYGON"


class EeFpType(str, Enum):
    SMD = "smd"
    THT = "tht"


class EePinType(int, Enum):
    UNSPECIFIED = 0
    INPUT = 1
    OUTPUT = 2
    BIDIRECTIONAL = 3
    POWER = 4


@dataclass
class Ee3dModelInfo:
    name: str
    uuid: str
    translation_x: float  # EE units
    translation_y: float  # EE units
    translation_z: float  # EE units
    rotation_x: float
    rotation_y: float
    rotation_z: float
