# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from enum import StrEnum

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.picker.jlcpcb.jlcpcb import Component
from faebryk.libs.picker.picker import PickError
from faebryk.libs.util import ConfigFlagEnum


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
