#!/usr/bin/env python3
"""Test impedance calculations against known reference values.

Reference values from common PCB calculators:
- Saturn PCB Toolkit
- EEWeb PCB Impedance Calculator
- Polar Instruments calculators
"""

import math


def microstrip_Z0(w_mm: float, h_mm: float, t_mm: float, er: float) -> float:
    """Calculate microstrip characteristic impedance using Hammerstad approximation."""
    h = max(h_mm, 1e-6)
    t = max(t_mm, 1e-6)
    w = max(w_mm, 1e-6)
    u = w / h
    a = (
        1
        + (1 / 49) * math.log((u**4 + (u / 52) ** 2) / (u**4 + 0.432))
        + (1 / 18.7) * math.log(1 + (u / 18.1) ** 3)
    )
    b = 0.564 * ((er - 0.9) / (er + 3)) ** 0.053
    eeff = (er + 1) / 2 + (er - 1) / 2 * (1 + 10 / u) ** (-a * b)
    du = t / math.pi / h * (1 + 1 / eeff) * math.log(1 + 4 * math.e / t * (h / w))
    u_eff = u + du
    if u_eff <= 1:
        return 60 / math.sqrt(eeff) * math.log(8 / u_eff + 0.25 * u_eff)
    return (
        120
        * math.pi
        / math.sqrt(eeff)
        / (u_eff + 1.393 + 0.667 * math.log(u_eff + 1.444))
    )


def stripline_Z0(w_mm: float, h_mm: float, t_mm: float, er: float) -> float:
    """Calculate stripline characteristic impedance (symmetric, Wheeler approx)."""
    h = max(h_mm, 1e-6)
    t = max(t_mm, 1e-6)
    w = max(w_mm, 1e-6)
    return 60.0 / math.sqrt(er) * math.log(1.9 * (4.0 * h / (0.8 * w + t)))


def find_width_for_impedance(
    target_z0: float, h_mm: float, t_mm: float, er: float, is_microstrip: bool
) -> float:
    """Binary search to find trace width for target impedance."""
    w_min = 0.01  # 10 um minimum
    w_max = 10.0  # 10 mm maximum

    for _ in range(100):  # iterations
        w = (w_min + w_max) / 2
        if is_microstrip:
            z = microstrip_Z0(w, h_mm, t_mm, er)
        else:
            z = stripline_Z0(w, h_mm, t_mm, er)

        if abs(z - target_z0) < 0.1:
            return w

        if z > target_z0:
            w_min = w
        else:
            w_max = w

    return w


def print_test_cases():
    """Print test cases with known reference values."""

    print("=" * 80)
    print("IMPEDANCE CALCULATION TEST CASES")
    print("=" * 80)

    # Test Case 1: Common 4-layer stackup (JLC4Layer from the example)
    print("\nTest Case 1: JLC 4-Layer Stackup")
    print("-" * 40)

    # Layer 1 (F.Cu) - Microstrip over 0.21mm FR4
    h_mm = 0.21  # 210um prepreg to In1.Cu
    t_mm = 0.035  # 35um copper
    er = 4.2

    print(f"F.Cu (Microstrip): h={h_mm}mm, t={t_mm}mm, Er={er}")

    # Calculate for 50 ohm single-ended (for 100 ohm differential)
    w_50 = find_width_for_impedance(50, h_mm, t_mm, er, is_microstrip=True)
    z_50 = microstrip_Z0(w_50, h_mm, t_mm, er)
    print(f"  50Ω trace: w={w_50:.3f}mm, Z0={z_50:.1f}Ω")
    print(f"  Reference (Saturn PCB): w≈0.38mm for 50Ω")

    # Layer 2 (In1.Cu) - Stripline between FR4 layers
    h_mm = (
        1.065 / 2
    )  # Distance to nearest reference plane (symmetric stripline assumption)
    t_mm = 0.0152  # 15.2um copper for inner layers

    print(f"\nIn1.Cu (Stripline): h={h_mm}mm, t={t_mm}mm, Er={er}")

    w_50_strip = find_width_for_impedance(50, h_mm, t_mm, er, is_microstrip=False)
    z_50_strip = stripline_Z0(w_50_strip, h_mm, t_mm, er)
    print(f"  50Ω trace: w={w_50_strip:.3f}mm, Z0={z_50_strip:.1f}Ω")
    print(f"  Reference (Saturn PCB): w≈0.22mm for 50Ω stripline")

    # Test Case 2: Standard values from industry
    print("\n" + "=" * 80)
    print("Test Case 2: Industry Standard Values")
    print("-" * 40)

    test_cases = [
        # (description, h_mm, t_mm, er, target_Z, is_microstrip, expected_w_mm)
        ("2-layer, 1.6mm FR4, 50Ω", 1.6, 0.035, 4.5, 50, True, 2.95),
        ("4-layer, 0.2mm prepreg, 50Ω", 0.2, 0.035, 4.2, 50, True, 0.37),
        ("Stripline, 0.5mm spacing, 50Ω", 0.5, 0.035, 4.2, 50, False, 0.23),
        ("USB diff pair, 90Ω diff (45Ω odd)", 0.2, 0.035, 4.2, 45, True, 0.43),
    ]

    for desc, h, t, er, z_target, is_micro, expected_w in test_cases:
        w_calc = find_width_for_impedance(z_target, h, t, er, is_micro)
        z_actual = (
            microstrip_Z0(w_calc, h, t, er)
            if is_micro
            else stripline_Z0(w_calc, h, t, er)
        )
        error = abs(w_calc - expected_w) / expected_w * 100

        print(f"\n{desc}:")
        print(f"  Calculated: w={w_calc:.3f}mm, Z0={z_actual:.1f}Ω")
        print(f"  Expected:   w≈{expected_w:.2f}mm")
        print(f"  Error:      {error:.1f}%")

    # Test Case 3: Differential pairs
    print("\n" + "=" * 80)
    print("Test Case 3: Differential Pair Calculations")
    print("-" * 40)

    print("\nFor 100Ω differential impedance:")
    print("  Odd-mode impedance ≈ 50Ω per trace")
    print("  Gap between traces affects coupling")
    print("\nTypical gaps for differential pairs:")
    print("  Microstrip: gap ≈ 2 × trace width")
    print("  Stripline:  gap ≈ 1.2 × trace width")

    # Check the actual stackup from the example
    print("\n" + "=" * 80)
    print("ACTUAL JLC 4-LAYER STACKUP ANALYSIS")
    print("-" * 40)

    layers = [
        ("F.Cu", "Copper", 0.035, None),  # index 1
        ("Prepreg", "FR4", 0.21, 4.2),  # index 2
        ("In1.Cu", "Copper", 0.0152, None),  # index 3
        ("Core", "FR4", 1.065, 4.2),  # index 4
        ("In2.Cu", "Copper", 0.0152, None),  # index 5
        ("Prepreg", "FR4", 0.21, 4.2),  # index 6
        ("B.Cu", "Copper", 0.035, None),  # index 7
    ]

    print("\nStackup structure:")
    for name, material, thickness, er in layers:
        if material == "Copper":
            print(f"  {name:10} {thickness * 1000:6.1f}μm {material}")
        else:
            print(f"  {name:10} {thickness * 1000:6.1f}μm {material} (εr={er})")

    print("\nCalculated trace widths for 50Ω (100Ω differential):")

    # F.Cu - microstrip over 210um FR4
    w_fcu = find_width_for_impedance(50, 0.21, 0.035, 4.2, True)
    print(f"  F.Cu:  w={w_fcu:.3f}mm (microstrip)")

    # In1.Cu - asymmetric stripline (210um up to F.Cu, 1065um down to In2.Cu)
    # Use closer reference for approximation
    w_in1 = find_width_for_impedance(50, 0.21, 0.0152, 4.2, False)
    print(f"  In1.Cu: w={w_in1:.3f}mm (stripline, nearest ref=210μm)")

    # In2.Cu - asymmetric stripline (1065um up to In1.Cu, 210um down to B.Cu)
    w_in2 = find_width_for_impedance(50, 0.21, 0.0152, 4.2, False)
    print(f"  In2.Cu: w={w_in2:.3f}mm (stripline, nearest ref=210μm)")

    # B.Cu - microstrip over 210um FR4
    w_bcu = find_width_for_impedance(50, 0.21, 0.035, 4.2, True)
    print(f"  B.Cu:  w={w_bcu:.3f}mm (microstrip)")


if __name__ == "__main__":
    print_test_cases()
