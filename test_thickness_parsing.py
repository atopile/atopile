#!/usr/bin/env python3
"""Test parsing of different thickness values."""

from faebryk.libs.units import Quantity as Q

test_values = [
    "35um",  # Outer layers
    "15.2um",  # Inner layers - with decimal
    "15um",  # Without decimal
    "0.0152mm",  # In mm
    15.2,  # Plain number
    Q("15.2um"),  # Pre-made Quantity
]


def parse_thickness(val):
    try:
        if isinstance(val, Q):
            return float(val.to("millimeter").m)
        if isinstance(val, str):
            # Try to parse as Quantity string
            try:
                q = Q(val)
                return float(q.to("millimeter").m)
            except Exception as e:
                print(f"    Failed to parse as Quantity: {e}")
        # Assume micrometers if plain number
        return float(val) / 1000.0
    except Exception as e:
        print(f"    Exception: {e}")
        return None


print("Testing thickness value parsing:")
print("=" * 50)

for val in test_values:
    print(f"\nInput: {val!r} (type: {type(val).__name__})")
    result = parse_thickness(val)
    if result is not None:
        print(f"  → {result:.4f}mm = {result * 1000:.1f}μm")
    else:
        print(f"  → FAILED TO PARSE")
