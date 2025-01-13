# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.module import Module

logger = logging.getLogger(__name__)


class is_not_pickable(Module.TraitT.decless()):
    """
    Mark module explicitly as not pickable.
    e.g MountingHoles that have static footprint and no parameters.
    """
