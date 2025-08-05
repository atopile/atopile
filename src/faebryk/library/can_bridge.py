# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from typing import Any

from faebryk.core.module import Module


class can_bridge(Module.TraitT):
    def bridge(self, _in, out):
        _in.connect(self.get_in())
        out.connect(self.get_out())

    @abstractmethod
    def get_in(self) -> Any: ...

    @abstractmethod
    def get_out(self) -> Any: ...
