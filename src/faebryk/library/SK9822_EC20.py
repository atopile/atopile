# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L


class SK9822_EC20(Module):
    """
    SK9822 is a two-wire transmission channel three
    (RGB) driving intelligent control circuit and
    the light emitting circuit in one of the LED light
    source control. Products containing a signal
    decoding module, data buffer, a built-in Constant
    current circuit and RC oscillator; CMOS, low
    voltage, low power consumption; 256 level grayscale
    PWM adjustment and 32 brightness adjustment;
    use the double output, Data and synchronization of
    the CLK signal, connected in series each wafer
    output action synchronization.
    """

    # interfaces
    power: F.ElectricPower
    sdo: F.ElectricLogic
    sdi: F.ElectricLogic
    cko: F.ElectricLogic
    ckl: F.ElectricLogic

    @L.rt_field
    def attach_to_footprint(self):
        x = self
        return F.can_attach_to_footprint_via_pinmap(
            {
                "1": x.sdo.line,
                "2": x.power.lv,
                "3": x.sdi.line,
                "4": x.ckl.line,
                "5": x.power.hv,
                "6": x.cko.line,
            }
        )

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(
            F.ElectricLogic.connect_all_module_references(self)
        )

    datasheet = L.f_field(F.has_datasheet_defined)(
        "https://datasheet.lcsc.com/lcsc/2110250930_OPSCO-Optoelectronics-SK9822-EC20_C2909059.pdf"
    )

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.LED
    )
