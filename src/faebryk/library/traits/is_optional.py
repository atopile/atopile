# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod

from faebryk.core.moduleinterface import ModuleInterface

logger = logging.getLogger(__name__)


class is_optional(ModuleInterface.TraitT):
    """
    Indicates that a module might not have a specific interface
    """

    @abstractmethod
    def is_needed(self) -> bool:
        """
        Returns whether it's needed
        """
        pass

    @abstractmethod
    def _handle_result(self, needed: bool) -> None:
        """
        Handles the result of the is_needed method once it's known
        """
        pass
