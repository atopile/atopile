# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Iterable, Sequence

from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.library.can_specialize import can_specialize

logger = logging.getLogger(__name__)


class can_specialize_defined(can_specialize.impl()):
    def __init__(
        self, specializable_types: Sequence[type["Module"] | type["ModuleInterface"]]
    ):
        super().__init__()
        self._specializable_types = specializable_types

    def get_specializable_types(
        self,
    ) -> Iterable[type["Module"] | type["ModuleInterface"]]:
        return self._specializable_types
