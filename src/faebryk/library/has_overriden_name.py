# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod


class has_overriden_name(Module.TraitT):
    @abstractmethod
    def get_name(self) -> str: ...
