# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import TYPE_CHECKING, Callable

from faebryk.libs.library import L

if TYPE_CHECKING:
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

logger = logging.getLogger(__name__)


class has_layout_transform(L.Module.TraitT.decless()):
    """
    Docstring describing your module
    """

    def __init__(self, transform: Callable[["PCB_Transformer"], None]):
        super().__init__()
        self.transform = transform
