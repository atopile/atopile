# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import StrEnum
from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile.errors import UserBadParameterError

logger = logging.getLogger(__name__)


class TestPoint(fabll.Node):
    """
    Basic test point.
    """

    class PadShape(StrEnum):
        CIRCLE = "circle"
        SQUARE = "rect"

    class PadType(StrEnum):
        SMD = "smd"
        THT = "thru_hole"

    # (pad_size, drill_size) combinations
    supported_sizes: list[tuple[float, float]] = [
        (1.0, 0.5),
        (1.5, 0.7),
        (2.0, 1.0),
        (2.5, 1.2),
        (3.0, 1.5),
        (4.0, 2.0),
    ]

    __test__ = False  # prevents pytest discovery

    contact = F.Electrical.MakeChild()

    pad_size = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    drill_size = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    pad_shape = F.Parameters.EnumParameter.MakeChild(enum_t=PadShape)
    pad_type = F.Parameters.EnumParameter.MakeChild(enum_t=PadType)

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
    _has_part_removed = fabll.Traits.MakeEdge(F.has_part_removed.MakeChild())

    _can_attatch_to_footprint = fabll.Traits.MakeEdge(
        F.Footprints.can_attach_to_footprint.MakeChild()
    )

    lead = F.Lead.is_lead.MakeChild()
    contact.add_dependant(fabll.Traits.MakeEdge(lead, [contact]))
    lead.add_dependant(
        fabll.Traits.MakeEdge(
            F.Lead.can_attach_to_pad_by_name.MakeChild(regex=r"1|contact"), [lead]
        )
    )

    designator_prefix = fabll.Traits.MakeEdge(
        F.has_designator_prefix.MakeChild(F.has_designator_prefix.Prefix.TP)
    )

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
            import TestPoint, ElectricSignal

            test_point = new TestPoint
            signal_to_test = new ElectricSignal

            # Connect to signal you want to probe
            signal_to_test.line ~ test_point.contact
            """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )

    @classmethod
    def MakeChild(
        cls,
        pad_size: float = 1.0,
        drill_size: float | None = None,
        pad_shape: PadShape = PadShape.CIRCLE,
        pad_type: PadType = PadType.SMD,
    ) -> fabll._ChildField[Self]:
        if pad_size not in [size for size, _ in cls.supported_sizes]:
            raise UserBadParameterError(
                f"Pad size {pad_size} is currently not supported for TestPoints. "
                "Supported pad sizes are: "
                f"{[size for size, _ in cls.supported_sizes]}"
            )
        if drill_size and drill_size not in [
            drill_size for _, drill_size in cls.supported_sizes
        ]:
            raise UserBadParameterError(
                f"Drill size {drill_size} is currently not supported for TestPoints. "
                "Supported drill sizes are: "
                f"{[drill_size for _, drill_size in cls.supported_sizes]}"
            )
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Numbers.MakeChild_ConstrainToSingleton(
                [out, cls.pad_size], pad_size
            )
        )
        if drill_size:
            out.add_dependant(
                F.Literals.Numbers.MakeChild_ConstrainToSingleton(
                    [out, cls.drill_size], drill_size
                )
            )
        out.add_dependant(
            F.Literals.AbstractEnums.MakeChild_ConstrainToLiteral(
                [out, cls.pad_shape], pad_shape
            )
        )
        out.add_dependant(
            F.Literals.AbstractEnums.MakeChild_ConstrainToLiteral(
                [out, cls.pad_type], pad_type
            )
        )
        return out
