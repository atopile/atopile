# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math

logger = logging.getLogger(__name__)


def sine_on_interval(
    interval: tuple[float, float],
) -> tuple[float, float]:
    """
    Computes the overall sine range on the given x-interval.

    The extreme values occur either at the endpoints or at turning points
    of sine (x = π/2 + π*k).
    """
    start, end = interval
    if start > end:
        raise ValueError("Invalid interval: start must be <= end")
    if math.isinf(start) or math.isinf(end):
        return (-1, 1)
    if end - start > 2 * math.pi:
        return (-1, 1)

    # Evaluate sine at the endpoints
    xs = [start, end]

    # Include turning points within the interval
    k_start = math.ceil((start - math.pi / 2) / math.pi)
    k_end = math.floor((end - math.pi / 2) / math.pi)
    for k in range(k_start, k_end + 1):
        xs.append(math.pi / 2 + math.pi * k)

    sine_values = [math.sin(x) for x in xs]
    return (min(sine_values), max(sine_values))
