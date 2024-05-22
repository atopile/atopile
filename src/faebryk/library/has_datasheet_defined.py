# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.has_datasheet import has_datasheet


class has_datasheet_defined(has_datasheet.impl()):
    def __init__(self, datasheet: str) -> None:
        super().__init__()
        self.datasheet = datasheet

    def get_datasheet(self) -> str:
        return self.datasheet
