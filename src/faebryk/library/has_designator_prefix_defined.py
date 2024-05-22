# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.has_designator_prefix import has_designator_prefix


class has_designator_prefix_defined(has_designator_prefix.impl()):
    def __init__(self, prefix: str) -> None:
        super().__init__()
        self.prefix = prefix

    def get_prefix(self) -> str:
        return self.prefix
