# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""Pure computational geometry helpers for custom pad anchor repositioning."""

import math

KI_PAD_SIZE_MIN = 0.001


def _is_on_segment(
    x0: float, y0: float, x1: float, y1: float, px: float, py: float
) -> bool:
    EPSILON = 1e-9
    return (
        min(x0, x1) <= px <= max(x0, x1)
        and min(y0, y1) <= py <= max(y0, y1)
        and abs((px - x0) * (y1 - y0) - (py - y0) * (x1 - x0)) < EPSILON
    )


def _is_left(x0: float, y0: float, x1: float, y1: float, px: float, py: float) -> bool:
    return ((x1 - x0) * (py - y0) - (y1 - y0) * (px - x0)) > 0


def _is_point_in_polygon(
    point: tuple[float, float], polygon: list[tuple[float, float]]
) -> bool:
    x, y = point
    winding_number = 0
    n = len(polygon)
    for i in range(n):
        x0, y0 = polygon[i]
        x1, y1 = polygon[(i + 1) % n]
        if _is_on_segment(x0, y0, x1, y1, x, y):
            return True
        if y0 <= y:
            if y1 > y and _is_left(x0, y0, x1, y1, x, y):
                winding_number += 1
        else:
            if y1 <= y and not _is_left(x0, y0, x1, y1, x, y):
                winding_number -= 1
    return winding_number != 0


def is_circle_in_polygon(
    center: tuple[float, float],
    radius: float,
    polygon: list[tuple[float, float]],
) -> bool:
    # Approximate circle with 12-sided polygon
    cx, cy = center
    return all(
        _is_point_in_polygon(
            (
                cx + radius * math.cos(2 * math.pi * i / 12),
                cy + radius * math.sin(2 * math.pi * i / 12),
            ),
            polygon,
        )
        for i in range(12)
    )


def find_anchor_position(
    polygon: list[tuple[float, float]], radius: float
) -> tuple[float, float] | None:
    min_x = min(p[0] for p in polygon)
    max_x = max(p[0] for p in polygon)
    min_y = min(p[1] for p in polygon)
    max_y = max(p[1] for p in polygon)
    STEP = 0.05
    x = min_x
    while x < max_x:
        y = min_y
        while y < max_y:
            if is_circle_in_polygon((x, y), radius, polygon):
                return (x, y)
            y += STEP
        x += STEP
    return None
