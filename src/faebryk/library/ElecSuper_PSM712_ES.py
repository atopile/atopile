# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.picker.picker import DescriptiveProperties
from faebryk.libs.units import P  # noqa: F401

logger = logging.getLogger(__name__)


class ElecSuper_PSM712_ES(Module):
    """
    RS485 bus ESD and surge protection

    17A 350W Bidirectional SOT-23
    ESD and Surge Protection (TVS/ESD) ROHS
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    rs485: F.RS485HalfDuplex

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    designator_prefix = L.f_field(F.has_designator_prefix_defined)(
        F.has_designator_prefix.Prefix.U
    )
    descriptive_properties = L.f_field(F.has_descriptive_properties_defined)(
        {
            DescriptiveProperties.manufacturer: "ElecSuper",
            DescriptiveProperties.partno: "PSM712-ES",
        }
    )
    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2209191800_ElecSuper-PSM712-ES_C5180294.pdf"
    )

    @L.rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.rs485.diff_pair.n.signal: ["1"],
                self.rs485.diff_pair.p.signal: ["2"],
                self.rs485.diff_pair.n.reference.lv: ["3"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------

        # ------------------------------------
        #          parametrization
        # ------------------------------------
        pass
