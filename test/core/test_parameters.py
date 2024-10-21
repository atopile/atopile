# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.parameter import Parameter
from faebryk.libs.library import L
from faebryk.libs.sets import Range
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


def test_new_definitions():
    _ = Parameter(
        units=P.ohm,
        domain=L.Domains.Numbers.REAL(negative=False),
        soft_set=Range(1 * P.ohm, 10 * P.Mohm),
        likely_constrained=True,
    )
