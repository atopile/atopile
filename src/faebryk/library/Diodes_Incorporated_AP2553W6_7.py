# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class Diodes_Incorporated_AP2553W6_7(F.Diodes_Incorporated_AP255x_x):
    """
    Power Distribution Switch. Mostly used in USB applications.
    - Active high enable
    - Current limit during overcurrent

    2.7V~5.5V 70mΩ 2.1A SOT-26
    """

    descriptive_properties = L.f_field(F.has_descriptive_properties_defined)(
        {
            DescriptiveProperties.manufacturer: "Diodes Incorporated",
            DescriptiveProperties.partno: "AP2553W6-7",
        }
    )
    lcsc_id = L.f_field(F.has_descriptive_properties_defined)({"LCSC": "C212302"})
