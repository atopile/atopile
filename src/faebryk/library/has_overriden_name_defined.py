# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.library.has_overriden_name import has_overriden_name


class has_overriden_name_defined(has_overriden_name.impl()):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.component_name = name

    def get_name(self):
        return self.component_name
