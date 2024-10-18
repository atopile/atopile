# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from abc import abstractmethod
from typing import Callable, Mapping

from faebryk.core.solver import Solver
import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.core.trait import TraitImpl
from faebryk.libs.picker.picker import PickError

logger = logging.getLogger(__name__)


class has_multi_picker(F.has_picker.impl()):
    def pick(self):
        module = self.get_obj(Module)
        es = []
        for _, picker in self.pickers:
            logger.debug(f"Trying picker for {module}: {picker}")
            try:
                picker.pick(module)
                logger.debug("Success")
                return
            except PickError as e:
                logger.debug(f"Fail: {e}")
                es.append(e)
        raise PickError(f"All pickers failed: {self.pickers}: {es}", module)

    class Picker:
        @abstractmethod
        def pick(self, module: Module): ...

    def __init__(self, prio: int, picker: Picker):
        super().__init__()
        self.pickers: list[tuple[int, has_multi_picker.Picker]] = [(prio, picker)]

    def __preinit__(self): ...

    class FunctionPicker(Picker):
        def __init__(self, picker: Callable[[Module, Solver], None], solver: Solver):
            self.picker = picker
            self.solver = solver

        def pick(self, module: Module) -> None:
            self.picker(module, self.solver)

        def __repr__(self) -> str:
            return f"{type(self).__name__}({self.picker.__name__})"

    @classmethod
    def add_pickers_by_type[T](
        cls,
        module: Module,
        lookup: Mapping[type, T],
        picker_factory: Callable[[T], Picker],
        base_prio: int = 0,
    ):
        prio = base_prio

        picker_types = [k for k in lookup if isinstance(module, k)]
        # sort by most specific first
        picker_types.sort(key=lambda x: len(x.__mro__), reverse=True)

        # only do most specific
        picker_types = picker_types[:1]

        for i, k in enumerate(picker_types):
            v = lookup[k]
            module.add(
                has_multi_picker(
                    # most specific first
                    prio + i,
                    picker_factory(v),
                )
            )

    def handle_duplicate(self, other: TraitImpl, node: Node) -> bool:
        if not isinstance(other, has_multi_picker):
            return super().handle_duplicate(other, node)

        other.pickers.extend(self.pickers)
        other.pickers.sort(key=lambda x: x[0])
        return False
