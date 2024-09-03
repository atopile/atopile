# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class SignalElectrical(F.Signal):
    # line is a better name, but for compatibility with Logic we use signal
    # might change in future
    signal: F.Electrical
    reference: F.ElectricPower
