# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto


class SMDSize(Enum):
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
        return self.table(to_metric=False)[self]

    @property
    def metric(self) -> "SMDSize":
        if self.name.startswith("M"):
            return self
        return self.table(to_metric=True)[self]

    @property
    def without_prefix(self) -> "str":
        return self.name[1:]
