# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod
from typing import TYPE_CHECKING, Iterable

from faebryk.core.trait import Trait

if TYPE_CHECKING:
    from faebryk.core.module import Module
    from faebryk.core.moduleinterface import ModuleInterface

logger = logging.getLogger(__name__)


class can_specialize(Trait):
    """
    Marks that a module can specialize other modules next to its bases.
    """

    @abstractmethod
    def get_specializable_types(
        self,
    ) -> Iterable[type["Module"] | type["ModuleInterface"]]:
        """
        Returns a list of types that can be specialized by this module (in addition to
        its own type and the types of its bases).
        """
        pass
