# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class has_kicad_manual_footprint(F.has_kicad_footprint.impl()):
    def __init__(self, str, pinmap: dict[F.Pad, str]) -> None:
        super().__init__()
        self.str = str
        self.pinmap = pinmap

    def get_kicad_footprint(self):
        return self.str

    def get_pin_names(self):
        return self.pinmap
