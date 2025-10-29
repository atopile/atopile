# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class has_datasheet_defined(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    def __init__(self, datasheet: str) -> None:
        super().__init__()
        self.datasheet = datasheet

    def get_datasheet(self) -> str:
        return self.datasheet
