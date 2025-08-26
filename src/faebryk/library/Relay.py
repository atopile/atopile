# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


# TODO: make generic (use Switch module, different switch models, bistable, etc.)
class Relay(Module):
    switch_a_nc: F.Electrical
    switch_a_common: F.Electrical
    switch_a_no: F.Electrical
    switch_b_no: F.Electrical
    switch_b_common: F.Electrical
    switch_b_nc: F.Electrical
    coil_power: F.ElectricPower

    coil_max_voltage = L.p_field(units=P.V)
    coil_max_current = L.p_field(units=P.A)
    coil_resistance = L.p_field(units=P.ohm)
    contact_max_switching_voltage = L.p_field(units=P.V)
    contact_max_switching_current = L.p_field(units=P.A)
    contact_max_current = L.p_field(units=P.A)

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.K
    )

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import Relay, ElectricPower, Diode, NFET, ElectricLogic

        relay = new Relay
        relay.coil_max_voltage = 12V
        relay.coil_max_current = 50mA
        relay.coil_resistance = 240ohm +/- 10%
        relay.contact_max_switching_voltage = 250V
        relay.contact_max_switching_current = 10A
        relay.contact_max_current = 16A

        # Connect coil power
        power_12v = new ElectricPower
        assert power_12v.voltage within 12V +/- 5%
        relay.coil_power ~ power_12v

        # Control relay with MOSFET and flyback diode
        control_mosfet = new NFET
        flyback_diode = new Diode
        control_signal = new ElectricLogic

        # Coil control circuit
        power_12v.hv ~ relay.coil_power.hv
        relay.coil_power.lv ~> control_mosfet ~> power_12v.lv
        control_signal ~ control_mosfet.gate

        # Flyback diode for coil protection
        relay.coil_power.hv ~ flyback_diode.cathode
        flyback_diode.anode ~ relay.coil_power.lv

        # Switch high-power load using normally open contact
        high_power_load ~ relay.switch_a_no
        relay.switch_a_common ~ high_voltage_supply
        """,
        language=F.has_usage_example.Language.ato,
    )
