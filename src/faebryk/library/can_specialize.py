# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from abc import abstractmethod
from typing import TYPE_CHECKING, Iterable

import faebryk.core.node as fabll

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class can_specialize(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()
    """
    Marks that a module can specialize other modules next to its bases.
    """

    @abstractmethod
    def get_specializable_types(
        self,
    ) -> Iterable[type[fabll.Module] | type[fabll.ModuleInterface]]:
        """
        Returns a list of types that can be specialized by this module (in addition to
        its own type and the types of its bases).
        """
        pass
