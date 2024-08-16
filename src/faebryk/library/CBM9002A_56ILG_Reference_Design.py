# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.Capacitor import Capacitor
from faebryk.library.CBM9002A_56ILG import CBM9002A_56ILG
from faebryk.library.Constant import Constant
from faebryk.library.Crystal_Oscillator import Crystal_Oscillator
from faebryk.library.Diode import Diode
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.I2C import I2C
from faebryk.library.USB2_0 import USB2_0
from faebryk.libs.units import P
from faebryk.libs.util import times


class CBM9002A_56ILG_Reference_Design(Module):
    """
    Minimal working example for the CBM9002A_56ILG
    """

    def __init__(self):
        super().__init__()

        # ----------------------------------------
        #     modules, interfaces, parameters
        # ----------------------------------------
        class _NODEs(Module.NODES()):
            mcu = CBM9002A_56ILG()
            reset_diode = Diode()
            reset_lowpass_cap = Capacitor()
            oscillator = Crystal_Oscillator()

        self.NODEs = _NODEs(self)

        class _PARAMs(Module.PARAMS()): ...

        self.PARAMs = _PARAMs(self)

        class _IFS(Module.IFS()):
            PA = times(8, ElectricLogic)
            PB = times(8, ElectricLogic)
            PD = times(8, ElectricLogic)
            usb = USB2_0()
            i2c = I2C()

            avcc = ElectricPower()
            vcc = ElectricPower()

            rdy = times(2, ElectricLogic)
            ctl = times(3, ElectricLogic)
            reset = ElectricLogic()
            wakeup = ElectricLogic()

            ifclk = ElectricLogic()
            clkout = ElectricLogic()
            xtalin = Electrical()
            xtalout = Electrical()

        self.IFs = _IFS(self)

        # ----------------------------------------
        #                traits
        # ----------------------------------------

        # ----------------------------------------
        #                aliases
        # ----------------------------------------
        gnd = self.IFs.vcc.IFs.lv

        # ----------------------------------------
        #                connections
        # ----------------------------------------
        # connect all mcu IFs to this module IFs
        for i, interface in enumerate(self.IFs.PA):
            interface.connect(self.NODEs.mcu.IFs.PA[i])
        for i, interface in enumerate(self.IFs.PB):
            interface.connect(self.NODEs.mcu.IFs.PB[i])
        for i, interface in enumerate(self.IFs.PD):
            interface.connect(self.NODEs.mcu.IFs.PD[i])
        self.IFs.usb.connect(self.NODEs.mcu.IFs.usb)
        self.IFs.i2c.connect(self.NODEs.mcu.IFs.i2c)
        self.IFs.avcc.connect(self.NODEs.mcu.IFs.avcc)
        self.IFs.vcc.connect(self.NODEs.mcu.IFs.vcc)
        for i, interface in enumerate(self.IFs.rdy):
            interface.connect(self.NODEs.mcu.IFs.rdy[i])
        for i, interface in enumerate(self.IFs.ctl):
            interface.connect(self.NODEs.mcu.IFs.ctl[i])
        self.IFs.reset.connect(self.NODEs.mcu.IFs.reset)
        self.IFs.wakeup.connect(self.NODEs.mcu.IFs.wakeup)
        self.IFs.ifclk.connect(self.NODEs.mcu.IFs.ifclk)
        self.IFs.clkout.connect(self.NODEs.mcu.IFs.clkout)
        self.IFs.xtalin.connect(self.NODEs.mcu.IFs.xtalin)
        self.IFs.xtalout.connect(self.NODEs.mcu.IFs.xtalout)

        self.IFs.reset.IFs.signal.connect_via(
            self.NODEs.reset_lowpass_cap, gnd
        )  # TODO: should come from a low pass for electric logic
        self.IFs.reset.get_trait(ElectricLogic.can_be_pulled).pull(up=True)
        self.IFs.reset.IFs.signal.connect_via(
            self.NODEs.reset_diode, self.IFs.vcc.IFs.hv
        )

        # crystal oscillator
        self.NODEs.oscillator.IFs.power.connect(self.IFs.vcc)
        self.NODEs.oscillator.IFs.n.connect(self.IFs.xtalin)
        self.NODEs.oscillator.IFs.p.connect(self.IFs.xtalout)

        # ----------------------------------------
        #               Parameters
        # ----------------------------------------
        self.NODEs.reset_lowpass_cap.PARAMs.capacitance.merge(Constant(1 * P.uF))

        self.NODEs.oscillator.NODEs.crystal.PARAMs.frequency.merge(
            Constant(24 * P.Mhertz)
        )
        self.NODEs.oscillator.NODEs.crystal.PARAMs.load_impedance.merge(
            Constant(12 * P.pohm)
        )
