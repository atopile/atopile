# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class has_overriden_name_defined(F.has_overriden_name.impl()):
    def __init__(self, name: str, explicit: bool = True) -> None:
        super().__init__()
        self.component_name = name
        self.explicit = explicit

    def get_name(self):
        return self.component_name

    def is_explicit(self) -> bool:
        return self.explicit
