#!/usr/bin/env python3
"""Reverse calculate what thickness would give us 2.70mm width."""

current_vcc = 0.9447  # A
width_seen = 2.70  # mm in the rules
j_limit_inner = 10.0  # A/mm² for inner layers

# Reverse calculation: thickness = current / (j_limit × width)
implied_thickness = current_vcc / (j_limit_inner * width_seen)

print(f"Given:")
print(f"  Current: {current_vcc}A")
print(f"  Width in rules: {width_seen}mm")
print(f"  Current density (inner): {j_limit_inner} A/mm²")
print()
print(
    f"Implied copper thickness: {implied_thickness:.4f}mm = {implied_thickness * 1000:.1f}μm"
)
print()
print(f"This is exactly: {implied_thickness / 0.035:.2f} × 35μm")
print()
print("So it seems like the inner layers are being calculated with 35μm thickness")
print("instead of the actual 15.2μm!")
print()
print("Or alternatively, the current density limit is being set to:")
calc_j = current_vcc / (0.0152 * width_seen)
print(f"  j_limit = {calc_j:.1f} A/mm²")
print(f"This is {calc_j / 10:.1f}× the expected 10 A/mm² for inner layers")
