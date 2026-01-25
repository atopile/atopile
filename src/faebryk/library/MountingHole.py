# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, StrEnum

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.iso_metric_screw_thread import Iso262_MetricScrewThreadSizes


class MountingHole(fabll.Node):
    """
    Mounting hole component for PCB mechanical attachment.

    Supports various metric screw sizes (M2 to M8) and pad configurations.
    """

    class PadType(StrEnum):
        NoPad = ""
        Pad = "Pad"
        Pad_TopBottom = "Pad_TopBottom"
        Pad_TopOnly = "Pad_TopOnly"
        Pad_Via = "Pad_Via"

    # We currently only have footprints for these sizes
    class SupportedMetricScrewSizes(Enum):
        M2 = Iso262_MetricScrewThreadSizes.M2.value
        M2_5 = Iso262_MetricScrewThreadSizes.M2_5.value
        M3 = Iso262_MetricScrewThreadSizes.M3.value
        M4 = Iso262_MetricScrewThreadSizes.M4.value
        M5 = Iso262_MetricScrewThreadSizes.M5.value
        M6 = Iso262_MetricScrewThreadSizes.M6.value
        M8 = Iso262_MetricScrewThreadSizes.M8.value

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    # Part is removed - mounting holes don't go through part picking
    has_part_removed = fabll.Traits.MakeEdge(F.has_part_removed.MakeChild())

    # Can attach to footprint
    _can_attach_to_footprint = fabll.Traits.MakeEdge(
        F.Footprints.can_attach_to_footprint.MakeChild()
    )

    # Designator prefix H for hardware/holes
    designator_prefix = fabll.Traits.MakeEdge(
        F.has_designator_prefix.MakeChild(F.has_designator_prefix.Prefix.H)
    )

    contact = F.Electrical.MakeChild()
    lead = F.Lead.is_lead.MakeChild()
    contact.add_dependant(fabll.Traits.MakeEdge(lead, [contact]))
    lead.add_dependant(
        fabll.Traits.MakeEdge(
            F.Lead.can_attach_to_pad_by_name.MakeChild(regex=r"1|contact"), [lead]
        )
    )

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
            example="""
        from "MountingHole.py" import MountingHole

        # M3 mounting hole with top and bottom pads
        m3_padded = new MountingHole<metric_screw_size="M3", pad_type="Pad">

        # M6 mounting hole without pads
        m6_no_pad = new MountingHole<metric_screw_size="M6", pad_type="NoPad">

        # M3 with top-only pad for grounding
        m3_top = new MountingHole<metric_screw_size="M3", pad_type="Pad_TopOnly">

        # Connect padded holes for grounding
        m3_padded.contact ~ m3_top.contact
        """,
            language=F.has_usage_example.Language.ato,
        ).put_on_type()
    )
