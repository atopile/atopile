# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


class AverageValue:
    """Measurement: compute mean of signal over capture window."""


class FinalValue:
    """Measurement: read last data point (transient) or OP value (DCOP)."""


class SettlingTime:
    """Measurement: time for signal to settle within tolerance of final value."""


class PeakToPeak:
    """Measurement: max - min of signal."""


class Overshoot:
    """Measurement: maximum percentage above final value."""


class RMS:
    """Measurement: root mean square of signal."""
