# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class TestPoint(Module):
    """
    Basic test point.
    """

    contact: F.Electrical

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.TP
    )

    def __preinit__(self):
        self.contact.add(F.requires_external_usage())

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import TestPoint

        test_point = new TestPoint

        # Connect to signal you want to probe
        signal_to_test ~ test_point.contact
        """,
        language=F.has_usage_example.Language.ato,
    )
