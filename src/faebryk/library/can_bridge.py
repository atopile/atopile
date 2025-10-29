# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from typing import Any

import faebryk.core.node as fabll
from faebryk.library.Electrical import Electrical


class can_bridge(fabll.Node):
    @classmethod
    def create_type(cls, tg: fabll.TypeGraph) -> None:
        cls._in = fabll.Child(nodetype=Electrical, tg=tg)
        cls.out = fabll.Child(nodetype=Electrical, tg=tg)

    def bridge(self, _in, out):
        _in.connect(self.get_in())
        out.connect(self.get_out())

    @abstractmethod
    def get_in(self) -> Any: ...

    @abstractmethod
    def get_out(self) -> Any: ...
