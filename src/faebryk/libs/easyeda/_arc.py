# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""SVG arc geometry: endpoint-to-center conversion and SVG path parsing."""

import math
import re


def compute_arc(
    start_x: float,
    start_y: float,
    radius_x: float,
    radius_y: float,
    angle: float,
    large_arc_flag: bool,
    sweep_flag: bool,
    end_x: float,
    end_y: float,
) -> tuple[float, float, float]:
    """
    Elliptical arc endpoint-to-center conversion (W3C SVG spec).
    Returns (center_x, center_y, angle_extent).
    """
    dx2 = (start_x - end_x) / 2.0
    dy2 = (start_y - end_y) / 2.0

    angle_rad = math.radians(angle % 360.0)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    x1 = cos_a * dx2 + sin_a * dy2
    y1 = -sin_a * dx2 + cos_a * dy2

    radius_x = abs(radius_x)
    radius_y = abs(radius_y)
    rx2 = radius_x * radius_x
    ry2 = radius_y * radius_y
    x1_2 = x1 * x1
    y1_2 = y1 * y1

    radii_check = (x1_2 / rx2 + y1_2 / ry2) if rx2 != 0 and ry2 != 0 else 0
    if radii_check > 1:
        radius_x *= math.sqrt(radii_check)
        radius_y *= math.sqrt(radii_check)
        rx2 = radius_x * radius_x
        ry2 = radius_y * radius_y

    sign = -1 if large_arc_flag == sweep_flag else 1
    sq = 0.0
    denom = rx2 * y1_2 + ry2 * x1_2
    if denom > 0:
        sq = (rx2 * ry2 - rx2 * y1_2 - ry2 * x1_2) / denom
    sq = max(sq, 0)
    coef = sign * math.sqrt(sq)
    cx1 = coef * ((radius_x * y1) / radius_y) if radius_y != 0 else 0
    cy1 = coef * -((radius_y * x1) / radius_x) if radius_x != 0 else 0

    sx2 = (start_x + end_x) / 2.0
    sy2 = (start_y + end_y) / 2.0
    cx = sx2 + (cos_a * cx1 - sin_a * cy1)
    cy = sy2 + (sin_a * cx1 + cos_a * cy1)

    ux = (x1 - cx1) / radius_x if radius_x != 0 else 0
    uy = (y1 - cy1) / radius_y if radius_y != 0 else 0
    vx = (-x1 - cx1) / radius_x if radius_x != 0 else 0
    vy = (-y1 - cy1) / radius_y if radius_y != 0 else 0

    n = math.sqrt((ux * ux + uy * uy) * (vx * vx + vy * vy))
    p = ux * vx + uy * vy
    cross_sign = -1 if (ux * vy - uy * vx) < 0 else 1

    if n != 0:
        p_n = max(-1.0, min(1.0, p / n))
        angle_extent = math.degrees(cross_sign * math.acos(p_n))
    else:
        angle_extent = 360 + 359

    if not sweep_flag and angle_extent > 0:
        angle_extent -= 360
    elif sweep_flag and angle_extent < 0:
        angle_extent += 360

    extent_sign = 1 if angle_extent < 0 else -1
    angle_extent = (abs(angle_extent) % 360) * extent_sign

    return cx, cy, angle_extent


def arc_midpoint(
    cx: float, cy: float, radius: float, angle_start: float, angle_end: float
) -> tuple[float, float]:
    mid_angle = (angle_start + angle_end) / 2
    return (
        cx + radius * math.cos(mid_angle),
        cy + radius * math.sin(mid_angle),
    )


def parse_svg_path_for_arc(
    path: str,
) -> tuple[float, float, tuple[float, float, float, bool, bool, float, float]] | None:
    """Parse an SVG path containing M...A... for arc conversion."""
    path = path.replace(",", " ")
    if "M" not in path or "A" not in path:
        return None

    parts = re.findall(r"([MA])([\s\d.eE+\-]+)", path)
    move_data = None
    arc_data = None
    for cmd, args in parts:
        nums = [float(x) for x in args.split()]
        if cmd == "M" and len(nums) >= 2:
            move_data = (nums[0], nums[1])
        elif cmd == "A" and len(nums) >= 7:
            arc_data = (
                nums[0],
                nums[1],
                nums[2],
                bool(nums[3]),
                bool(nums[4]),
                nums[5],
                nums[6],
            )

    if move_data is None or arc_data is None:
        return None

    return move_data[0], move_data[1], arc_data


# ── Tests ─────────────────────────────────────────────────────────────────────

import pytest  # noqa: E402


def test_compute_arc_quarter_circle():
    r = 5
    cx, cy, extent = compute_arc(
        start_x=r,
        start_y=0,
        radius_x=r,
        radius_y=r,
        angle=0,
        large_arc_flag=False,
        sweep_flag=True,
        end_x=0,
        end_y=r,
    )
    assert cx == pytest.approx(0.0, abs=0.1)
    assert cy == pytest.approx(0.0, abs=0.1)
    assert abs(extent) == pytest.approx(90.0, abs=1.0)


def test_compute_arc_small():
    cx, cy, extent = compute_arc(
        start_x=10,
        start_y=0,
        radius_x=10,
        radius_y=10,
        angle=0,
        large_arc_flag=False,
        sweep_flag=False,
        end_x=0,
        end_y=-10,
    )
    assert cx == pytest.approx(0.0, abs=0.5)
    assert cy == pytest.approx(0.0, abs=0.5)
    assert abs(extent) == pytest.approx(90.0, abs=2.0)


def test_compute_arc_zero_radius():
    cx, cy, _extent = compute_arc(0, 0, 0, 0, 0, False, False, 1, 1)
    assert math.isfinite(cx)
    assert math.isfinite(cy)


def test_compute_arc_large_vs_small():
    _, _, ext_small = compute_arc(10, 0, 10, 10, 0, False, True, 0, 10)
    _, _, ext_large = compute_arc(10, 0, 10, 10, 0, True, True, 0, 10)
    assert abs(ext_large) > abs(ext_small)


def test_compute_arc_sweep_direction():
    _, _, ext_cw = compute_arc(10, 0, 10, 10, 0, False, True, 0, 10)
    _, _, ext_ccw = compute_arc(10, 0, 10, 10, 0, False, False, 0, 10)
    assert ext_cw * ext_ccw < 0


def test_compute_arc_real_world():
    cx, cy, extent = compute_arc(
        start_x=3990.1575,
        start_y=3002.8605,
        radius_x=2.8648,
        radius_y=2.8648,
        angle=0,
        large_arc_flag=False,
        sweep_flag=False,
        end_x=3990.1768,
        end_y=2997.1406,
    )
    assert math.isfinite(cx)
    assert math.isfinite(cy)
    assert math.isfinite(extent)
