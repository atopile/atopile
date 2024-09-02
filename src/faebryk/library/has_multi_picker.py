# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from abc import abstractmethod
from typing import Callable, Mapping

import faebryk.library._F as F
from faebryk.core.module import Module
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

    def __preinit__(self):
        self.pickers: list[tuple[int, has_multi_picker.Picker]] = []

    def add_picker(self, prio: int, picker: Picker):
        self.pickers.append((prio, picker))
        self.pickers = sorted(self.pickers, key=lambda x: x[0])

    @classmethod
    def add_to_module(cls, module: Module, prio: int, picker: Picker):
        if not module.has_trait(F.has_picker):
            module.add_trait(cls())

        t = module.get_trait(F.has_picker)
        assert isinstance(t, has_multi_picker)
        t.add_picker(prio, picker)

    class FunctionPicker(Picker):
        def __init__(self, picker: Callable[[Module], None]):
            self.picker = picker

        def pick(self, module: Module) -> None:
            self.picker(module)

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
            cls.add_to_module(
                module,
                # most specific first
                prio + i,
                picker_factory(v),
            )
