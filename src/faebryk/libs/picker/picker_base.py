# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Base classes for the picker module, extracted to avoid circular imports.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import faebryk.core.node as fabll
    from faebryk.libs.picker.localpick import PickerOption


class PickSupplier(ABC):
    supplier_id: str

    @abstractmethod
    def attach(self, module: "fabll.Node", part: "PickerOption"): ...


@dataclass(frozen=True)
class PickedPart:
    manufacturer: str
    partno: str
    supplier_partno: str
    supplier: PickSupplier
