# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import faebryk.core.node as fabll


# TODO this is still very early phase
#  need to write somewhere the auto construct logic
#  either trigger it by param merge or at pick time or so
class has_construction_dependency(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    class NotConstructable(Exception): ...

    class NotConstructableYet(NotConstructable): ...

    class NotConstructableEver(NotConstructable): ...

    def __preinit__(self) -> None:
        self.executed = False

    def construct(self):
        if self.executed:
            return
        self._construct()
        self._fulfill()

    @abstractmethod
    def _construct(self): ...

    def _fulfill(self):
        self.executed = True

    def is_implemented(self):
        return not self.executed
