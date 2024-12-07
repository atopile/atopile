# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from enum import Enum

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.units import P
from faebryk.core.parameter import R
from faebryk.libs.util import cast_assert

logger = logging.getLogger(__name__)


class I2S(ModuleInterface):
    sd: F.ElectricLogic    # Serial Data
    ws: F.ElectricLogic    # Word Select (Left/Right Clock)
    sck: F.ElectricLogic   # Serial Clock

    sample_rate = L.p_field(units=P.hertz, domain=R.Domains.Numbers.NATURAL())
    bit_depth = L.p_field(units=P.bit, domain=R.Domains.Numbers.NATURAL())

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    class SampleRate(Enum):
        rate_8k = 8 * P.khertz
        rate_44k1 = 44.1 * P.khertz
        rate_48k = 48 * P.khertz
        rate_96k = 96 * P.khertz
        rate_192k = 192 * P.khertz

    class BitDepth(Enum):
        depth_16 = 16
        depth_24 = 24
        depth_32 = 32

    @staticmethod
    def define_max_sample_rate_capability(rate: SampleRate):
        return F.Range(I2S.SampleRate.rate_8k, rate)

    def __preinit__(self) -> None:
        self.sample_rate.add(
            F.is_dynamic_by_connections(lambda mif: cast_assert(I2S, mif).sample_rate)
        )
        self.bit_depth.add(
            F.is_dynamic_by_connections(lambda mif: cast_assert(I2S, mif).bit_depth)
        )
