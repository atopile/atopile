# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod


class has_datasheet(Module.TraitT):
    @abstractmethod
    def get_datasheet(self) -> str: ...
