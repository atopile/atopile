# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class has_datasheet_defined(F.has_datasheet.impl()):
    def __init__(self, datasheet: str) -> None:
        super().__init__()
        self.datasheet = datasheet

    def get_datasheet(self) -> str:
        return self.datasheet
