# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Iterable, Sequence

import faebryk.core.node as fabll
from faebryk.library.can_specialize import can_specialize

logger = logging.getLogger(__name__)


class can_specialize_defined(can_specialize.impl()):
    def __init__(
        self,
        specializable_types: Sequence[type[fabll.Module] | type[fabll.ModuleInterface]],
    ):
        super().__init__()
        self._specializable_types = specializable_types

    def get_specializable_types(
        self,
    ) -> Iterable[type[fabll.Module] | type[fabll.ModuleInterface]]:
        return self._specializable_types
