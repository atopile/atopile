# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.parameter import R
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class I2S(ModuleInterface):
    sd: F.ElectricLogic  # Serial Data
    ws: F.ElectricLogic  # Word Select (Left/Right Clock)
    sck: F.ElectricLogic  # Serial Clock

    sample_rate = L.p_field(units=P.hertz, domain=R.Domains.Numbers.NATURAL())
    bit_depth = L.p_field(units=P.bit, domain=R.Domains.Numbers.NATURAL())

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.sd.line.add(F.has_net_name("SD", level=F.has_net_name.Level.SUGGESTED))
        self.ws.line.add(F.has_net_name("WS", level=F.has_net_name.Level.SUGGESTED))
        self.sck.line.add(F.has_net_name("SCK", level=F.has_net_name.Level.SUGGESTED))

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import I2S, ElectricPower

        i2s = new I2S
        i2s.sample_rate = 44100Hz  # Common rates: 8k, 16k, 22k, 44.1k, 48k, 96k Hz
        i2s.bit_depth = 16bit      # Common depths: 16, 24, 32 bit

        # Connect power reference for logic levels
        power_3v3 = new ElectricPower
        assert power_3v3.voltage within 3.3V +/- 5%
        i2s.sd.reference ~ power_3v3   # Serial Data
        i2s.ws.reference ~ power_3v3   # Word Select (Left/Right Clock)
        i2s.sck.reference ~ power_3v3  # Serial Clock (Bit Clock)

        # Connect to microcontroller I2S peripheral
        microcontroller.i2s_sd ~ i2s.sd.line
        microcontroller.i2s_ws ~ i2s.ws.line
        microcontroller.i2s_sck ~ i2s.sck.line

        # Connect to audio codec or DAC/ADC
        audio_codec.i2s ~ i2s

        # I2S timing relationships:
        # - SCK frequency = sample_rate * bit_depth * 2 (stereo)
        # - WS frequency = sample_rate (toggles left/right channel)
        # - SD carries time-multiplexed audio data

        # Common applications: digital audio, microphones, speakers
        """,
        language=F.has_usage_example.Language.ato,
    )
