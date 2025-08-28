#!/usr/bin/env python3
"""Debug the actual rule generation to see what values are being calculated."""

import math


def _mm_str(val_mm: float) -> str:
    """Format mm value for KiCad rules."""
    return f"{val_mm:.2f}mm"


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


def _stripline_w_for_z0(z0: float, h_mm: float, t_mm: float, er: float) -> float:
    w_min = 1e-3
    w_max = max(10 * h_mm, 1e-3)
    z_min = stripline_Z0(w_min, h_mm, t_mm, er)
    z_max = stripline_Z0(w_max, h_mm, t_mm, er)
    tries = 0
    while (z_min - z0) * (z_max - z0) > 0 and tries < 6:
        w_max *= 2
        z_max = stripline_Z0(w_max, h_mm, t_mm, er)
        tries += 1
    w = (w_min + w_max) / 2
    for _ in range(60):
        z = stripline_Z0(w, h_mm, t_mm, er)
        if abs(z - z0) < 0.1:
            break
        if z > z0:
            w_min = w
        else:
            w_max = w
        w = (w_min + w_max) / 2
    return max(w, w_min)


def _gap_default(is_outer: bool, w_mm: float) -> float:
    return (2.0 * w_mm) if is_outer else (1.2 * w_mm)


def simulate_rule_generation():
    """Simulate what the rule generation code is doing."""

    print("SIMULATING DIFFERENTIAL PAIR RULE GENERATION")
    print("=" * 60)

    # JLC 4-layer stackup copper layers with thicknesses
    copper_layers = [
        (1, 0.035),  # F.Cu - index 1, thickness 35um
        (3, 0.0152),  # In1.Cu - index 3, thickness 15.2um
        (5, 0.0152),  # In2.Cu - index 5, thickness 15.2um
        (7, 0.035),  # B.Cu - index 7, thickness 35um
    ]

    layer_names = ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]

    zdiff = 100.0  # Target differential impedance
    zodd = zdiff / 2.0  # Odd-mode impedance
    min_track_mm = 0.15

    print(f"Target differential impedance: {zdiff}Ω")
    print(f"Odd-mode impedance: {zodd}Ω")
    print(f"Minimum track width: {min_track_mm}mm")
    print()

    # Test what _nearest_dielectric_props would return for each layer
    # Based on the stackup, these are the expected values:
    dielectric_props = {
        1: (0.21, 4.2),  # F.Cu: 210um to In1.Cu
        3: (0.21, 4.2),  # In1.Cu: 210um to F.Cu (closer than 1065um to In2.Cu)
        5: (0.21, 4.2),  # In2.Cu: 210um to B.Cu (closer than 1065um to In1.Cu)
        7: (0.21, 4.2),  # B.Cu: 210um to In2.Cu
    }

    for i, (stack_idx, t_mm) in enumerate(copper_layers):
        is_outer = i == 0 or i == len(copper_layers) - 1
        layer_name = layer_names[i]
        h_mm, er = dielectric_props[stack_idx]

        print(f"\n{layer_name} (stack_idx={stack_idx}):")
        print(f"  Is outer layer: {is_outer}")
        print(f"  Copper thickness: {t_mm}mm")
        print(f"  Dielectric to ref: {h_mm}mm")
        print(f"  Dielectric Er: {er}")

        # Calculate trace width for odd-mode impedance
        if is_outer:
            w_mm = _microstrip_w_for_z0(zodd, h_mm, t_mm, er)
            actual_z = microstrip_Z0(w_mm, h_mm, t_mm, er)
            print(f"  Using microstrip formula")
        else:
            w_mm = _stripline_w_for_z0(zodd, h_mm, t_mm, er)
            actual_z = stripline_Z0(w_mm, h_mm, t_mm, er)
            print(f"  Using stripline formula")

        print(f"  Calculated width: {w_mm:.3f}mm -> Z0={actual_z:.1f}Ω")

        # Calculate gap
        s_mm = _gap_default(is_outer, w_mm)
        print(f"  Calculated gap: {s_mm:.3f}mm")

        # Apply minimum constraints (this is what causes the 0.15mm!)
        w_mm_constrained = max(min_track_mm, w_mm)
        s_mm_constrained = max(0.15, s_mm)

        print(f"  After constraints:")
        print(
            f"    Width: {w_mm_constrained:.3f}mm"
            + (" (CLAMPED!)" if w_mm < min_track_mm else "")
        )
        print(
            f"    Gap: {s_mm_constrained:.3f}mm"
            + (" (CLAMPED!)" if s_mm < 0.15 else "")
        )

        print(f"  Rule output:")
        print(f"    (constraint track_width (opt {_mm_str(w_mm_constrained)}))")
        print(f"    (constraint diff_pair_gap (opt {_mm_str(s_mm_constrained)}))")


if __name__ == "__main__":
    simulate_rule_generation()
