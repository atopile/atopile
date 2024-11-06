# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from enum import StrEnum
from typing import Iterable

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.parameter import Parameter
from faebryk.libs.picker.jlcpcb.jlcpcb import Component
from faebryk.libs.picker.lcsc import attach
from faebryk.libs.picker.picker import (
    PickError,
    has_part_picked,
    has_part_picked_defined,
)
from faebryk.libs.util import ConfigFlagEnum

logger = logging.getLogger(__name__)


class PickerType(StrEnum):
    JLCPCB = "jlcpcb"
    API = "api"


DB_PICKER_BACKEND = ConfigFlagEnum(
    PickerType, "PICKER", PickerType.JLCPCB, "Picker backend to use"
)


class StaticPartPicker(F.has_multi_picker.Picker, ABC):
    def __init__(
        self,
        *,
        mfr: str | None = None,
        mfr_pn: str | None = None,
        lcsc_pn: str | None = None,
    ) -> None:
        super().__init__()
        self.mfr = mfr
        self.mfr_pn = mfr_pn
        self.lcsc_pn = lcsc_pn

    def _friendly_description(self) -> str:
        desc = []
        if self.mfr:
            desc.append(f"mfr={self.mfr}")
        if self.mfr_pn:
            desc.append(f"mfr_pn={self.mfr_pn}")
        if self.lcsc_pn:
            desc.append(f"lcsc_pn={self.lcsc_pn}")
        return ", ".join(desc) or "<no params>"

    @abstractmethod
    def _find_parts(self, module: Module) -> list[Component]:
        pass

    def pick(self, module: Module):
        parts = self._find_parts(module)

        if len(parts) > 1:
            raise PickError(
                f"Multiple parts found for {self._friendly_description()}", module
            )

        if len(parts) < 1:
            raise PickError(
                f"Could not find part for {self._friendly_description()}", module
            )

        (part,) = parts
        try:
            part.attach(module, [])
        except ValueError as e:
            raise PickError(
                f"Could not attach part for {self._friendly_description()}", module
            ) from e


def _try_merge_params(target: Module, source: Module) -> bool:
    assert type(target) is type(source)

    # Override module parameters with picked component parameters
    module_params: dict[str, tuple[Parameter, Parameter]] = (
        target.zip_children_by_name_with(source, sub_type=Parameter)
    )

    # sort by type to avoid merge conflicts
    types_sort = [F.ANY, F.TBD, F.Constant, F.Range, F.Set, F.Operation]
    it = sorted(
        module_params.values(),
        key=lambda x: types_sort.index(type(x[0].get_most_narrow())),
    )
    for p, value in it:
        if not value.is_subset_of(p):
            return False
    for p, value in it:
        p.override(value)

    return True


class CachePicker(F.has_multi_picker.Picker):
    def __init__(self):
        super().__init__()
        self.cache = defaultdict[type[Module], set[Module]](set)

    def pick(self, module: Module):
        mcache = [m for m in self.cache[type(module)] if m.has_trait(has_part_picked)]
        for m in mcache:
            if _try_merge_params(module, m):
                logger.debug(f"Found compatible part in cache: {module} with {m}")
                module.add(
                    F.has_descriptive_properties_defined(
                        m.get_trait(F.has_descriptive_properties).get_properties()
                    )
                )
                part = m.get_trait(has_part_picked).get_part()
                attach(module, part.partno)
                module.add(has_part_picked_defined(part))
                return

        self.cache[type(module)].add(module)
        raise PickError(f"No compatible part found in cache for {module}", module)

    @staticmethod
    def add_to_modules(modules: Iterable[Module], prio: int = 0):
        picker = CachePicker()
        for m in modules:
            m.add(F.has_multi_picker(prio, picker))
