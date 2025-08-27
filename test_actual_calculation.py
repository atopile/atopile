#!/usr/bin/env python3
"""Test what the actual code path would calculate."""

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


def _microstrip_w_for_z0(z0: float, h_mm: float, t_mm: float, er: float) -> float:
    # Bisection over width
    w_min = 1e-3
    w_max = max(10 * h_mm, 1e-3)
    z_min = microstrip_Z0(w_min, h_mm, t_mm, er)
    z_max = microstrip_Z0(w_max, h_mm, t_mm, er)
    tries = 0
    while (z_min - z0) * (z_max - z0) > 0 and tries < 6:
        w_max *= 2
        z_max = microstrip_Z0(w_max, h_mm, t_mm, er)
        tries += 1
    w = (w_min + w_max) / 2
    for _ in range(60):
        z = microstrip_Z0(w, h_mm, t_mm, er)
        if abs(z - z0) < 0.1:
            break
        if z > z0:
            w_min = w
        else:
            w_max = w
        w = (w_min + w_max) / 2
    return max(w, w_min)


# Test with actual values that would be passed
print("Testing actual impedance calculations:")
print("=" * 60)

# What _nearest_dielectric_props SHOULD return for F.Cu if working correctly
h_mm = 0.2  # This is what the function returns as fallback!
t_mm = 0.035
er = 4.2
zodd = 50.0

print(f"\nF.Cu calculation (h={h_mm}mm fallback):")
print(f"  Input: h={h_mm}mm, t={t_mm}mm, er={er}, Z_target={zodd}Ω")
w_mm = _microstrip_w_for_z0(zodd, h_mm, t_mm, er)
actual_z = microstrip_Z0(w_mm, h_mm, t_mm, er)
print(f"  Result: w={w_mm:.3f}mm -> Z0={actual_z:.1f}Ω")
print(f"  After min constraint (0.15mm): w={max(0.15, w_mm):.3f}mm")

# What it SHOULD calculate with correct h=0.21mm
h_mm_correct = 0.21
print(f"\nF.Cu calculation (h={h_mm_correct}mm correct):")
print(f"  Input: h={h_mm_correct}mm, t={t_mm}mm, er={er}, Z_target={zodd}Ω")
w_mm_correct = _microstrip_w_for_z0(zodd, h_mm_correct, t_mm, er)
actual_z_correct = microstrip_Z0(w_mm_correct, h_mm_correct, t_mm, er)
print(f"  Result: w={w_mm_correct:.3f}mm -> Z0={actual_z_correct:.1f}Ω")
print(f"  After min constraint (0.15mm): w={max(0.15, w_mm_correct):.3f}mm")

# Check if the issue is the fallback value
print(
    f"\n** The function is returning h={h_mm}mm (fallback) instead of {h_mm_correct}mm! **"
)
print(
    f"This causes w={w_mm:.3f}mm to be calculated, which gets clamped to 0.15mm minimum."
)
