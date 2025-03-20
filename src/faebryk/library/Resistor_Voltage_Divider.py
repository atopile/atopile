# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from deprecated import deprecated

import faebryk.library._F as F

Resistor_Voltage_Divider = deprecated(
    reason="Use ResistorVoltageDivider instead",
)(F.ResistorVoltageDivider)
