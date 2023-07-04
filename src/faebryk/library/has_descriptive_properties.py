# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import ModuleTrait


class has_descriptive_properties(ModuleTrait):
    def get_properties(self) -> dict[str, str]:
        raise NotImplementedError()

    def add_properties(self, properties: dict[str, str]):
        raise NotImplementedError()
