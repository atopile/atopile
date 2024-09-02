# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.module import Module


class has_descriptive_properties(Module.TraitT):
    def get_properties(self) -> dict[str, str]:
        raise NotImplementedError()

    def add_properties(self, properties: dict[str, str]):
        raise NotImplementedError()
