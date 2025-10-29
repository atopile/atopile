# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Iterable, Sequence

import faebryk.core.node as fabll

logger = logging.getLogger(__name__)


class can_specialize_defined(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    def __init__(
        self,
        specializable_types: Sequence[type[fabll.Module] | type[fabll.ModuleInterface]],
    ):
        self._specializable_types = specializable_types

    def get_specializable_types(
        self,
    ) -> Iterable[type[fabll.Module] | type[fabll.ModuleInterface]]:
        return self._specializable_types
