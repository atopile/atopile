# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class TestPoint(fabll.Node):
    """
    Basic test point.
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    contact = F.Electrical.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.is_module.MakeChild()

    designator_prefix = F.has_designator_prefix.MakeChild(
        F.has_designator_prefix.Prefix.TP
    )

    usage_example = F.has_usage_example.MakeChild(
        example="""
        import TestPoint, ElectricSignal

        test_point = new TestPoint
        signal_to_test = new ElectricSignal

        # Connect to signal you want to probe
        signal_to_test.line ~ test_point.contact
        """,
        language=F.has_usage_example.Language.ato,
    ).put_on_type()
