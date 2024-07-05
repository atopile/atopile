# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Generic, TypeVar

from faebryk.core.core import (
    _ModuleTrait,
)
from faebryk.library.Footprint import Footprint

TF = TypeVar("TF", bound="Footprint")


class _FootprintTrait(Generic[TF], _ModuleTrait[TF]): ...


class FootprintTrait(_FootprintTrait["Footprint"]): ...
