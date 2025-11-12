# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class Relay(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    switch_a_nc = F.Electrical.MakeChild()
    switch_a_common = F.Electrical.MakeChild()
    switch_a_no = F.Electrical.MakeChild()
    switch_b_no = F.Electrical.MakeChild()
    switch_b_common = F.Electrical.MakeChild()
    switch_b_nc = F.Electrical.MakeChild()
    coil_power = F.ElectricPower.MakeChild()

    contact_max_switching_voltage = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Volt
    )
    contact_max_switching_current = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Ampere
    )
    contact_max_current = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)
    # TODO: make generic (use Switch module, different switch models, bistable, etc.)
    # switch = [F.Switch.MakeChild() for _ in range(6)]

    coil_max_voltage = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Volt)
    coil_max_current = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)
    coil_resistance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ohm)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.is_module.MakeChild()

    designator_prefix = F.has_designator_prefix.MakeChild(
        F.has_designator_prefix.Prefix.K
    )

    S = F.has_simple_value_representation.Spec
    _simple_repr = F.has_simple_value_representation.MakeChild(
        S(coil_max_voltage, prefix="Coil"),
        #     S(switch.get().max_voltage, prefix="Sw"),
        #     S(switch.get().max_current, prefix="Sw"),
    )

    _usage_example = F.has_usage_example.MakeChild(
        example="""
        import Relay, ElectricPower, Diode, MOSFET, ElectricLogic

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
        control_mosfet = new MOSFET
        control_mosfet.channel_type = "N_CHANNEL"
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
    ).put_on_type()
