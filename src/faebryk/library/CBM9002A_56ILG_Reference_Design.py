# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P


class CBM9002A_56ILG_Reference_Design(Module):
    """
    Minimal working example for the CBM9002A_56ILG
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    mcu: F.CBM9002A_56ILG
    reset_diode: F.Diode
    reset_lowpass_cap: F.Capacitor
    oscillator: F.Crystal_Oscillator

    PA = L.list_field(8, F.ElectricLogic)
    PB = L.list_field(8, F.ElectricLogic)
    PD = L.list_field(8, F.ElectricLogic)
    usb: F.USB2_0
    i2c: F.I2C

    avcc: F.ElectricPower
    vcc: F.ElectricPower

    rdy = L.list_field(2, F.ElectricLogic)
    ctl = L.list_field(3, F.ElectricLogic)
    reset: F.ElectricLogic
    wakeup: F.ElectricLogic

    ifclk: F.ElectricLogic
    clkout: F.ElectricLogic
    xtalin: F.Electrical
    xtalout: F.Electrical

    # ----------------------------------------
    #                traits
    # ----------------------------------------

    # ----------------------------------------
    #                connections
    # ----------------------------------------
    def __preinit__(self):
        gnd = self.vcc.lv
        self.connect_interfaces_by_name(self.mcu, allow_partial=True)

        self.reset.signal.connect_via(
            self.reset_lowpass_cap, gnd
        )  # TODO: should come from a low pass for electric logic
        self.reset.pulled.pull(up=True)
        self.reset.signal.connect_via(self.reset_diode, self.vcc.hv)

        # crystal oscillator
        self.oscillator.power.connect(self.vcc)
        self.oscillator.n.connect(self.xtalin)
        self.oscillator.p.connect(self.xtalout)

        # ----------------------------------------
        #               Parameters
        # ----------------------------------------
        self.reset_lowpass_cap.capacitance.merge(F.Constant(1 * P.uF))

        self.oscillator.crystal.frequency.merge(F.Constant(24 * P.Mhertz))
        self.oscillator.crystal.frequency_tolerance.merge(
            F.Range.upper_bound(20 * P.ppm)
        )

        # TODO: just set to a 1N4148
        self.reset_diode.forward_voltage.merge(715 * P.mV)
        self.reset_diode.reverse_leakage_current.merge(1 * P.uA)
        self.reset_diode.current.merge(300 * P.mA)
        self.reset_diode.max_current.merge(1 * P.A)
