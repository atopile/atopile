#!/usr/bin/env python3
"""Test the actual current width calculations."""


def _compute_min_width_from_current(
    current_a: float,
    copper_thickness_mm: float,
    is_outer: bool,
    min_track_mm: float,
    delta_t_c: float | None = None,
) -> float:
    if current_a <= 0:
        return min_track_mm
    j_limit = 20.0 if is_outer else 10.0  # A/mm^2 baseline
    if delta_t_c is not None:
        j_limit *= max(0.5, min(1.5, 10.0 / max(1.0, delta_t_c)))
    width_mm = current_a / (j_limit * max(1e-6, copper_thickness_mm))
    return max(min_track_mm, width_mm)


# Test with actual values from the build
copper_layers = [
    (1, 0.035),  # F.Cu
    (3, 0.0152),  # In1.Cu
    (5, 0.0152),  # In2.Cu
    (7, 0.035),  # B.Cu
]

current_vcc = 0.9447  # A
min_track = 0.15  # mm

print("Testing current width calculations for VCC (0.9447A):")
print("=" * 60)

for i, (stack_idx, t_mm) in enumerate(copper_layers):
    layer_names = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
    is_outer = i == 0 or i == len(copper_layers) - 1

    width = _compute_min_width_from_current(
        current_vcc,
        t_mm,
        is_outer,
        min_track,
    )

    # Show the calculation
    j_limit = 20.0 if is_outer else 10.0
    calc_width = current_vcc / (j_limit * t_mm)

    print(f"\n{layer_names[i]} (index {stack_idx}):")
    print(f"  Copper thickness: {t_mm}mm")
    print(f"  Is outer: {is_outer}")
    print(f"  Current density limit: {j_limit} A/mm²")
    print(
        f"  Calculation: {current_vcc:.4f} / ({j_limit} × {t_mm}) = {calc_width:.3f}mm"
    )
    print(f"  After min constraint: {width:.3f}mm")

print("\n" + "=" * 60)
print("Expected vs Actual in rules:")
print("  F.Cu:    Expected 1.35mm, Rules show 1.35mm ✓")
print("  In1.Cu:  Expected 6.21mm, Rules show 2.70mm ✗")
print("  In2.Cu:  Expected 6.21mm, Rules show 2.70mm ✗")
print("  B.Cu:    Expected 1.35mm, Rules show 1.35mm ✓")
print("\nThe inner layers are showing 2.70mm instead of 6.21mm!")
print("This is exactly 2× the outer layer width, suggesting")
print("something is overriding the calculation.")
