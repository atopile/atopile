# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""Unit conversion and coordinate transforms for EasyEDA → KiCad."""

import math


def _to_mm(dim: float) -> float:
    """Convert EasyEDA internal units to mm."""
    return float(dim) * 10 * 0.0254


def _fp_to_ki(dim: str | float) -> float:
    """Convert EasyEDA raw units (possibly string) to KiCad mm, rounded."""
    try:
        return round(_to_mm(float(dim)), 2)
    except (ValueError, TypeError):
        return 0.0


def _angle_to_ki(rotation: float) -> float:
    if math.isnan(rotation):
        return 0.0
    return -(360 - rotation) if rotation > 180 else rotation


def _fp_xy(x: float, y: float, bbox_x: float, bbox_y: float) -> tuple[float, float]:
    """Footprint coordinate: subtract bbox origin, round to 2dp."""
    return round(x - bbox_x, 2), round(y - bbox_y, 2)


def _sym_xy(x: float, y: float, bbox_x: float, bbox_y: float) -> tuple[float, float]:
    """Symbol coordinate: subtract bbox, flip Y, convert EE→mm, round to 2dp."""
    return (
        round(_to_mm(int(x) - int(bbox_x)), 2),
        round(-_to_mm(int(y) - int(bbox_y)), 2),
    )


_MIN_STROKE_W = 0.01


# ── Tests ─────────────────────────────────────────────────────────────────────

import pytest  # noqa: E402


def test_to_mm():
    assert _to_mm(0) == 0
    # 100 * 10 * 0.0254 = 25.4
    assert _to_mm(100) == pytest.approx(25.4, abs=0.01)
    assert _to_mm(1000) == pytest.approx(254.0, abs=0.1)


def test_to_mm_negative():
    assert _to_mm(-100) == pytest.approx(-25.4, abs=0.01)


def test_fp_to_ki_conversion():
    assert _fp_to_ki(0) == 0
    assert _fp_to_ki("100") == pytest.approx(25.4, abs=0.01)
    assert _fp_to_ki("invalid") == 0.0
