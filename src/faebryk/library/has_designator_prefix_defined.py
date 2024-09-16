# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class has_designator_prefix_defined(F.has_designator_prefix.impl()):
    def __init__(self, prefix: str | F.has_designator_prefix.Prefix) -> None:
        super().__init__()
        self.prefix = prefix

    def get_prefix(self) -> str:
        return self.prefix
