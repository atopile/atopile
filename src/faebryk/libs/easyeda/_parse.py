# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""Shared parsing helpers for tilde-delimited EasyEDA field lists."""


def get(f: list[str], idx: int, default: str = "") -> str:
    """Safe index into a tilde-split field list."""
    return f[idx] if idx < len(f) else default


def bool_field(val: str) -> bool:
    if not val:
        return False
    if val == "show":
        return True
    try:
        return bool(float(val))
    except (ValueError, TypeError):
        return bool(val)


def parse_float(val: str, default: float = 0.0) -> float:
    if not val:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def parse_int(val: str, default: int = 0) -> int:
    if not val:
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def text_is_displayed(val: str) -> bool:
    # LEGACY: empty string → True matches the old Pydantic model's default validator.
    if val == "":
        return True
    return bool_field(val)


def has_fill(f: list[str], idx: int) -> bool:
    raw = get(f, idx)
    return bool(raw and raw.lower() != "none")


# ── Tests ─────────────────────────────────────────────────────────────────────

import pytest  # noqa: E402


def test_bool_field():
    assert bool_field("") is False
    assert bool_field("show") is True
    assert bool_field("1") is True
    assert bool_field("0") is False
    assert bool_field("Y") is True


def test_parse_float():
    assert parse_float("3.14") == pytest.approx(3.14)
    assert parse_float("") == 0.0
    assert parse_float("", default=5.0) == 5.0
    assert parse_float("invalid") == 0.0


def test_parse_int():
    assert parse_int("42") == 42
    assert parse_int("3.7") == 3
    assert parse_int("") == 0
    assert parse_int("invalid") == 0
