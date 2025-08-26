# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging

import faebryk.library._F as F
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.units import P
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


class DifferentialSignal(ModuleInterface):
    pair: F.DifferentialPair
    timing_delay = L.p_field(units=P.ps)
    single_ended_impedance = L.p_field(units=P.Ω)
    differential_impedance = L.p_field(units=P.Ω)

    def __preinit__(self):
        self.pair.n.line.impedance.alias_is(self.single_ended_impedance)
        self.pair.p.line.impedance.alias_is(self.single_ended_impedance)


class DifferentialSignals(ModuleInterface):
    """
    DifferentialSignals is a module that contains a list of DifferentialSignals
    - all pairs have the same impedance and delay
    """

    inter_pair_delay = L.p_field(units=P.ps)
    intra_pair_delay = L.p_field(units=P.ps)
    single_ended_impedance = L.p_field(units=P.Ω)
    differential_impedance = L.p_field(units=P.Ω)

    @L.rt_field
    def pairs(self):
        return times(self._pair_count, DifferentialSignal)

    def __init__(self, pair_count: int):
        self._pair_count = pair_count

    def __preinit__(self):
        for pair in self.pairs:
            pair.timing_delay.alias_is(self.intra_pair_delay)
            pair.single_ended_impedance.alias_is(self.single_ended_impedance)
            pair.differential_impedance.alias_is(self.differential_impedance)


class Ethernet(ModuleInterface):
    """
    1000BASE-T Gigabit Ethernet Interface
    """

    # Ethernet pairs
    pairs = L.f_field(DifferentialSignals)(pair_count=4)

    # Status LEDs
    led_speed: F.ElectricLogic  # Speed LED
    led_link: F.ElectricLogic  # Link LED

    def __preinit__(self):
        self.pairs.single_ended_impedance.constrain_subset(L.Range(45 * P.Ω, 55 * P.Ω))
        self.pairs.differential_impedance.constrain_subset(L.Range(90 * P.Ω, 100 * P.Ω))
        self.pairs.inter_pair_delay.constrain_subset(L.Range(0.5 * P.ps, 1.5 * P.ps))
        self.pairs.intra_pair_delay.constrain_subset(L.Range(0.5 * P.ps, 1.5 * P.ps))

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.led_speed.line.add(
            F.has_net_name("ETH_LED_SPEED", level=F.has_net_name.Level.SUGGESTED)
        )
        self.led_link.line.add(
            F.has_net_name("ETH_LED_LINK", level=F.has_net_name.Level.SUGGESTED)
        )
        for i, pair in enumerate(self.pairs):
            pair.p.line.add(
                F.has_net_name(f"ETH_P{i}", level=F.has_net_name.Level.SUGGESTED)
            )
            pair.n.line.add(
                F.has_net_name(f"ETH_P{i}", level=F.has_net_name.Level.SUGGESTED)
            )

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import Ethernet, ElectricPower

        ethernet = new Ethernet

        # Connect power reference for logic levels
        power_3v3 = new ElectricPower
        ethernet.led_speed.reference ~ power_3v3
        ethernet.led_link.reference ~ power_3v3

        # Connect to PHY or connector
        # Four differential pairs for 1000BASE-T
        ethernet_connector.tx_pairs[0] ~ ethernet.pairs[0]
        ethernet_connector.tx_pairs[1] ~ ethernet.pairs[1]
        ethernet_connector.rx_pairs[2] ~ ethernet.pairs[2]
        ethernet_connector.rx_pairs[3] ~ ethernet.pairs[3]

        # Connect status LEDs
        ethernet.led_speed ~ speed_led_output
        ethernet.led_link ~ link_led_output
        """,
        language=F.has_usage_example.Language.ato,
    )
