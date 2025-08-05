# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.libs.library import L


class PowerSwitchMOSFET(F.PowerSwitch):
    """
    Power switch using a MOSFET

    This power switch uses an NMOS when lowside, and a PMOS when highside.
    """

    def __init__(self, lowside: bool, normally_closed: bool) -> None:
        super().__init__(normally_closed=normally_closed)

        self._lowside = lowside

    # components

    mosfet: F.MOSFET

    def __preinit__(self):
        self.mosfet.channel_type.constrain_subset(
            F.MOSFET.ChannelType.N_CHANNEL
            if self._lowside
            else F.MOSFET.ChannelType.P_CHANNEL
        )
        self.mosfet.saturation_type.constrain_subset(
            F.MOSFET.SaturationType.ENHANCEMENT
        )

        # pull gate
        # lowside     normally_closed   pull up
        # True        True              True
        # True        False             False
        # False       True              False
        # False       False             True
        self.logic_in.pulled.pull(self._lowside == self._normally_closed, owner=self)

        # connect gate to logic
        self.logic_in.line.connect(self.mosfet.gate)

        # passthrough non-switched side, bridge switched side
        if self._lowside:
            self.power_in.hv.connect(self.switched_power_out.hv)
            self.power_in.lv.connect_via(self.mosfet, self.switched_power_out.lv)
        else:
            self.power_in.lv.connect(self.switched_power_out.lv)
            self.power_in.hv.connect_via(self.mosfet, self.switched_power_out.hv)

        # TODO do more with logic
        #   e.g check reference being same as power

    # ----------------------------------------
    #              usage example
    # ----------------------------------------
    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import PowerSwitchMOSFET, ElectricPower

        # High-side power switch controlled by logic
        pwr_sw = new PowerSwitchMOSFET
        supply   = new ElectricPower
        load_pwr = new ElectricPower

        supply   ~ pwr_sw.power_in
        pwr_sw.switched_power_out ~ load_pwr
        """,
        language=F.has_usage_example.Language.ato,
    )
