# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.link import Link
from faebryk.core.moduleinterface import ModuleInterface


class has_single_connection(ModuleInterface.TraitT):
    @abstractmethod
    def get_connection(self) -> Link: ...
