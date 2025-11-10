# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.units import P


class Crystal_Oscillator(fabll.Node):
    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    crystal = F.Crystal.MakeChild()
    capacitors = [F.Capacitor.MakeChild() for _ in range(2)]
    current_limiting_resistor = F.Resistor.MakeChild()
    xtal_if = F.XtalIF.MakeChild()

    # https://blog.adafruit.com/2012/01/24/choosing-the-right-crystal-and-caps-for-your-design/
    # http://www.st.com/internet/com/TECHNICAL_RESOURCES/TECHNICAL_LITERATURE/APPLICATION_NOTE/CD00221665.pdf
    _STRAY_CAPACITANCE = fabll.Parameter.MakeChild_Numeric(
        unit=F.Units.Farad,
    )

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.is_module.MakeChild()

    # ----------------------------------------
    #                WIP
    # ----------------------------------------

    def capacitance(self):
        return (self.crystal.load_capacitance - self._STRAY_CAPACITANCE) * 2

    def __preinit__(self):
        for cap in self.capacitors:
            cap.capacitance.constrain_subset(self.capacitance)

        self.current_limiting_resistor.allow_removal_if_zero()
        self.crystal.gnd.connect(self.xtal_if.gnd)
        self.crystal.unnamed[0].connect_via(self.capacitors[0], self.xtal_if.gnd)
        self.crystal.unnamed[1].connect_via(self.capacitors[1], self.xtal_if.gnd)

        self.crystal.unnamed[0].connect_via(
            self.current_limiting_resistor, self.xtal_if.xout
        )
        self.crystal.unnamed[1].connect(self.xtal_if.xin)

        _can_bridge = F.can_bridge.MakeChild(
            in_=self.xtal_if.get().xin, out_=self.xtal_if.get().xout
        )

    usage_example = F.has_usage_example.MakeChild(
        example="""
        import Crystal_Oscillator, ElectricPower

        crystal_osc = new Crystal_Oscillator

        # Configure crystal parameters
        crystal_osc.crystal.frequency = 16MHz +/- 20ppm
        crystal_osc.crystal.load_capacitance = 18pF +/- 10%
        crystal_osc.crystal.equivalent_series_resistance = 80ohm +/- 20%
        crystal_osc.crystal.package = "HC49U"

        # Connect power for ground reference
        power_3v3 = new ElectricPower
        assert power_3v3.voltage within 3.3V +/- 5%
        crystal_osc.xtal_if.gnd ~ power_3v3.lv

        # Connect to microcontroller crystal pins
        microcontroller.xtal_in ~ crystal_osc.xtal_if.xin
        microcontroller.xtal_out ~ crystal_osc.xtal_if.xout

        # Load capacitors are automatically calculated:
        # C_load = (Crystal_load_cap - Stray_cap) * 2
        # Typically results in 22pF capacitors for 18pF crystal

        # Current limiting resistor prevents overdrive (optional)
        crystal_osc.current_limiting_resistor.resistance = 1kohm +/- 5%

        # Common frequencies: 8MHz, 12MHz, 16MHz, 20MHz, 25MHz
        # Used for: microcontroller clocks, RTC, timing references
        """,
        language=F.has_usage_example.Language.ato,
    )
