# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto


class SMDSize(Enum):
    class UnableToConvert(Exception): ...

    I01005 = auto()
    I0201 = auto()
    I0402 = auto()
    I0603 = auto()
    I0805 = auto()
    I1206 = auto()
    I1210 = auto()
    I1808 = auto()
    I1812 = auto()
    I1825 = auto()
    I2220 = auto()
    I2225 = auto()
    I3640 = auto()

    M0402 = auto()
    M0603 = auto()
    M1005 = auto()
    M1608 = auto()
    M2012 = auto()
    M3216 = auto()
    M3225 = auto()
    M4520 = auto()
    M4532 = auto()
    M4564 = auto()
    M5750 = auto()
    M5664 = auto()
    M9110 = auto()

    SMD4x4mm = "SMD,4x4mm"
    SMD6x6mm = "SMD,6x6mm"
    SMD5x5mm = "SMD,5x5mm"
    SMD3x3mm = "SMD,3x3mm"
    SMD8x8mm = "SMD,8x8mm"
    SMD12x12mm = "SMD,12x12mm"
    SMD12_5x12_5mm = "SMD,12.5x12.5mm"
    SMD7_8x7mm = "SMD,7.8x7mm"
    SMD4_5x4mm = "SMD,4.5x4mm"
    SMD11_5x10mm = "SMD,11.5x10mm"
    SMD6_6x7mm = "SMD,6.6x7mm"
    SMD7x6_6mm = "SMD,7x6.6mm"
    SMD5_8x5_2mm = "SMD,5.8x5.2mm"
    SMD6_6x7_3mm = "SMD,6.6x7.3mm"
    SMD3_5x3mm = "SMD,3.5x3mm"
    SMD7_3x7_3mm = "SMD,7.3x7.3mm"
    SMD6_6x7_1mm = "SMD,6.6x7.1mm"
    SMD7x7mm = "SMD,7x7mm"
    SMD5_4x5_2mm = "SMD,5.4x5.2mm"
    SMD6_7x6_7mm = "SMD,6.7x6.7mm"
    SMD11x10mm = "SMD,11x10mm"
    SMD10x11mm = "SMD,10x11mm"
    SMD5_2x5_8mm = "SMD,5.2x5.8mm"
    SMD4_4x4_2mm = "SMD,4.4x4.2mm"
    SMD13_8x12_6mm = "SMD,13.8x12.6mm"
    SMD10_1x10_1mm = "SMD,10.1x10.1mm"
    SMD13_5x12_6mm = "SMD,13.5x12.6mm"
    SMD4_7x4_7mm = "SMD,4.7x4.7mm"
    SMD12_3x12_3mm = "SMD,12.3x12.3mm"
    SMD12_6x13_5mm = "SMD,12.6x13.5mm"
    SMD2_8x2_9mm = "SMD,2.8x2.9mm"
    SMD7_3x6_6mm = "SMD,7.3x6.6mm"
    SMD2_5x2mm = "SMD,2.5x2mm"
    SMD4_9x4_9mm = "SMD,4.9x4.9mm"
    SMD10_2x10mm = "SMD,10.2x10mm"
    SMD7_1x6_6mm = "SMD,7.1x6.6mm"
    SMD10x10mm = "SMD,10x10mm"
    SMD5_7x5_7mm = "SMD,5.7x5.7mm"
    SMD4_1x4_1mm = "SMD,4.1x4.1mm"
    SMD4_1x4_5mm = "SMD,4.1x4.5mm"
    SMD7x7_8mm = "SMD,7x7.8mm"
    SMD10x9mm = "SMD,10x9mm"
    SMD0_6x1_2mm = "SMD,0.6x1.2mm"
    SMD6_5x6_9mm = "SMD,6.5x6.9mm"
    SMD1_6x2mm = "SMD,1.6x2mm"
    SMD2x2_5mm = "SMD,2x2.5mm"
    SMD7_1x6_5mm = "SMD,7.1x6.5mm"
    SMD8x8_5mm = "SMD,8x8.5mm"
    SMD4_5x4_1mm = "SMD,4.5x4.1mm"
    SMD4_2x4_4mm = "SMD,4.2x4.4mm"
    SMD10_4x10_3mm = "SMD,10.4x10.3mm"
    SMD10x11_5mm = "SMD,10x11.5mm"
    SMD13_5x12_8mm = "SMD,13.5x12.8mm"
    SMD17_2x17_2mm = "SMD,17.2x17.2mm"
    SMD5_2x5_4mm = "SMD,5.2x5.4mm"
    SMD11_6x10_1mm = "SMD,11.6x10.1mm"
    SMD10_5x10_3mm = "SMD,10.5x10.3mm"
    SMD7_2x6_6mm = "SMD,7.2x6.6mm"
    SMD10x10_2mm = "SMD,10x10.2mm"
    SMD7_8x7_8mm = "SMD,7.8x7.8mm"
    SMD1_7x2_3mm = "SMD,1.7x2.3mm"
    SMD5_2x5_7mm = "SMD,5.2x5.7mm"
    SMD2x2mm = "SMD,2x2mm"
    SMD4_5x5_2mm = "SMD,4.5x5.2mm"
    SMD9x10mm = "SMD,9x10mm"
    SMD2_5x2_9mm = "SMD,2.5x2.9mm"
    SMD4_6x4_1mm = "SMD,4.6x4.1mm"
    SMD7_5x7_5mm = "SMD,7.5x7.5mm"
    SMD5_5x5_2mm = "SMD,5.5x5.2mm"
    SMD6_4x6_6mm = "SMD,6.4x6.6mm"
    SMD12_5x13_5mm = "SMD,12.5x13.5mm"
    SMD10_7x10mm = "SMD,10.7x10mm"
    SMD5_5x5_3mm = "SMD,5.5x5.3mm"
    SMD10_1x11_6mm = "SMD,10.1x11.6mm"
    SMD10_3x10_5mm = "SMD,10.3x10.5mm"
    SMD3_2x3mm = "SMD,3.2x3mm"
    SMD6_6x6_4mm = "SMD,6.6x6.4mm"
    SMD1_2x0_6mm = "SMD,1.2x0.6mm"
    SMD1_2x1_8mm = "SMD,1.2x1.8mm"
    SMD5x5_2mm = "SMD,5x5.2mm"
    SMD8_3x8_3mm = "SMD,8.3x8.3mm"
    SMD10_2x10_8mm = "SMD,10.2x10.8mm"
    SMD2_5x3_2mm = "SMD,2.5x3.2mm"
    SMD4x4_5mm = "SMD,4x4.5mm"
    SMD8_5x8mm = "SMD,8.5x8mm"
    SMD3_5x3_2mm = "SMD,3.5x3.2mm"
    SMD12_9x13_2mm = "SMD,12.9x13.2mm"
    SMD8_8x8_2mm = "SMD,8.8x8.2mm"
    SMD4_1x4_4mm = "SMD,4.1x4.4mm"
    SMD10_8x10mm = "SMD,10.8x10mm"
    SMD10_5x10mm = "SMD,10.5x10mm"
    SMD1_1x1_8mm = "SMD,1.1x1.8mm"
    SMD7_5x7mm = "SMD,7.5x7mm"
    SMD3_8x3_8mm = "SMD,3.8x3.8mm"
    SMD1_6x2_2mm = "SMD,1.6x2.2mm"
    SMD12_2x12_2mm = "SMD,12.2x12.2mm"
    SMD4_8x4_8mm = "SMD,4.8x4.8mm"
    SMD5_7x5_4mm = "SMD,5.7x5.4mm"
    SMD15_5x16_5mm = "SMD,15.5x16.5mm"
    SMD8_2x8_8mm = "SMD,8.2x8.8mm"
    SMD10x14mm = "SMD,10x14mm"
    SMD5_1x5_4mm = "SMD,5.1x5.4mm"
    SMD16_5x15_5mm = "SMD,16.5x15.5mm"
    SMD2_1x3mm = "SMD,2.1x3mm"
    SMD10x11_6mm = "SMD,10x11.6mm"
    SMD3_2x4mm = "SMD,3.2x4mm"
    SMD7_2x7_9mm = "SMD,7.2x7.9mm"
    SMD5_8x5_8mm = "SMD,5.8x5.8mm"
    SMD6_6x7_4mm = "SMD,6.6x7.4mm"
    SMD12_7x12_7mm = "SMD,12.7x12.7mm"
    SMD1_2x2mm = "SMD,1.2x2mm"
    SMD1x1_7mm = "SMD,1x1.7mm"
    SMD4_4x4_1mm = "SMD,4.4x4.1mm"
    SMD4_2x4_2mm = "SMD,4.2x4.2mm"

    @staticmethod
    def table(
        to_metric: bool,
    ) -> "dict[SMDSize, SMDSize]":
        table = {
            SMDSize.M0402: SMDSize.I01005,
            SMDSize.M0603: SMDSize.I0201,
            SMDSize.M1005: SMDSize.I0402,
            SMDSize.M1608: SMDSize.I0603,
            SMDSize.M2012: SMDSize.I0805,
            SMDSize.M3216: SMDSize.I1206,
            SMDSize.M3225: SMDSize.I1210,
            SMDSize.M4520: SMDSize.I1808,
            SMDSize.M4532: SMDSize.I1812,
            SMDSize.M4564: SMDSize.I1825,
            SMDSize.M5750: SMDSize.I2220,
            SMDSize.M5664: SMDSize.I2225,
            SMDSize.M9110: SMDSize.I3640,
        }

        if to_metric:
            return {v: k for k, v in table.items()}
        return table

    @property
    def imperial(self) -> "SMDSize":
        if self.name.startswith("I"):
            return self

        try:
            return self.table(to_metric=False)[self]
        except KeyError:
            raise self.UnableToConvert(f"Unable to convert {self} to imperial")

    @property
    def metric(self) -> "SMDSize":
        if self.name.startswith("M"):
            return self

        try:
            return self.table(to_metric=True)[self]
        except KeyError:
            raise self.UnableToConvert(f"Unable to convert {self} to metric")

    @property
    def without_prefix(self) -> "str":
        name = self.name
        for prefix in ["I", "M"]:
            name = name.removeprefix(prefix)
        return name
