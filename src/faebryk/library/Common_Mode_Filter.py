# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class Common_Mode_Filter(Module):
    c_a = L.list_field(2, F.Electrical)
    c_b = L.list_field(2, F.Electrical)

    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.FL
    )
