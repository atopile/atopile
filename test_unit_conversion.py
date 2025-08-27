#!/usr/bin/env python3
"""Test unit conversion from ato stackup values."""

# The stackup defines values like:
# stackup.layers[2].thickness = 210um

# This likely comes through as a Quantity object
from faebryk.libs.units import Quantity as Q

# Test various potential values
test_values = [
    210,  # Plain number (assume um)
    Q("210um"),  # Quantity with um
    Q("0.21mm"),  # Quantity with mm
    "210um",  # String
]


def _to_mm_any(val) -> float | None:
    try:
        if isinstance(val, Q):
            return float(val.to("millimeter").m)
        if val is None:
            return None
        # Assume micrometers if no unit
        return float(val) / 1000.0
    except Exception as e:
        print(f"  ERROR: {e}")
        return None


print("Testing unit conversion:")
print("=" * 50)
for val in test_values:
    print(f"\nInput: {val} (type: {type(val).__name__})")
    result = _to_mm_any(val)
    print(f"Output: {result}mm")

# Test what the actual ato values might be
print("\n" + "=" * 50)
print("Testing actual stackup values:")

# From Stackup.ato:
# stackup.layers[2].thickness = 210um
# This is likely parsed as Q("210um")

thickness_210um = Q("210um")
print(f"\n210um as Quantity: {thickness_210um}")
print(f"Converted to mm: {_to_mm_any(thickness_210um)}mm")

thickness_35um = Q("35um")
print(f"\n35um as Quantity: {thickness_35um}")
print(f"Converted to mm: {_to_mm_any(thickness_35um)}mm")
