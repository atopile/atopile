# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
import faebryk.libs.library.L as L
from faebryk.core.module import Module
from faebryk.libs.units import P


class Battery(Module):
    # TODO: Deprecated voltage -> rated_voltage
    rated_voltage = L.p_field(
        units=P.V,
        soft_set=L.Range(0 * P.V, 100 * P.V),
        likely_constrained=True,
    )
    # TODO: Deprecated capacity -> rated_capacity
    rated_capacity = L.p_field(
        units=P.Ah,
        soft_set=L.Range(100 * P.mAh, 100 * P.Ah),
        likely_constrained=True,
    )
    # TODO: Deprecated discharge_rate -> rated_discharge_rate
    rated_discharge_rate = L.p_field(
        units=P.A,
        soft_set=L.Range(1 * P.C, 10 * P.C),  # TODO: Cleanup
        likely_constrained=True,
    )
    # TODO: Deprecated c_rate -> rated_c_rate
    rated_c_rate = L.p_field(
        units=P.dimensionless,
        soft_set=L.Range(1 * P.C, 10 * P.C),
        likely_constrained=True,
    )

    capacity = L.deprecated_field(message="Use rated_capacity instead")
    voltage = L.deprecated_field(message="Use rated_voltage instead")

    # TODO: equations to connect c rate discharge and capacity

    power: F.ElectricPower

    @L.rt_field
    def pickable(self):
        return F.is_pickable_by_type(
            endpoint=F.is_pickable_by_type.Endpoint.BATTERIES,
            params=[
                self.rated_voltage,
                self.rated_capacity,
                self.rated_discharge_rate,
                self.rated_c_rate,
            ],
        )

    def __preinit__(self) -> None:
        self.power.voltage.constrain_subset(self.rated_voltage)

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(self.power)

    designator = L.f_field(F.has_designator_prefix)("BAT")

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import Battery, ElectricPower

        battery = new Battery
        battery.voltage = 3.7V +/- 10%  # Li-ion cell
        battery.capacity = 2000mAh +/- 5%

        # Connect to system power
        system_power = new ElectricPower
        battery.power ~ system_power

        # Battery specifications will constrain system voltage
        assert system_power.voltage within battery.voltage

        # For multiple cells in series
        battery_pack = new Battery
        battery_pack.voltage = 11.1V +/- 10%  # 3S Li-ion pack
        battery_pack.capacity = 2000mAh +/- 5%
        """,
        language=F.has_usage_example.Language.ato,
    )
