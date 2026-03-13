# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Transmission line impedance calculators.

Ported from published IEEE paper formulas, using KiCad's
common/transline_calculations/ as a verification reference.

All dimensions are in SI meters unless otherwise noted.

References:
- Hammerstad & Jensen, "Accurate Models for Microstrip Computer-Aided
  Design", IEEE MTT-S Digest, 1980.
- Kirschning & Jansen, "Accurate Wide-Range Design Equations for the
  Frequency-Dependent Characteristic of Parallel Coupled Microstrip
  Lines", IEEE Trans. MTT, vol. 32, no. 1, Jan. 1984.
- S.B. Cohn, "Shielded Coupled-Strip Transmission Line",
  IRE Trans. MTT, vol. 3, no. 5, Oct. 1955.
- S.B. Cohn, "Characteristic Impedance of the Shielded-Strip
  Transmission Line", IRE Trans. MTT, vol. 2, no. 2, Jul. 1954.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
C0 = 299792458.0  # speed of light in vacuum [m/s]
MU0 = 4.0e-7 * math.pi  # permeability of free space [H/m]
E0 = 1.0 / (MU0 * C0 * C0)  # permittivity of free space [F/m]
ZF0 = MU0 * C0  # impedance of free space ≈ 376.73 Ω


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AnalysisResult:
    """Result of single-ended transmission line analysis."""

    z0: float  # characteristic impedance [Ω]
    er_eff: float  # effective dielectric constant


@dataclass(frozen=True)
class DifferentialAnalysisResult:
    """Result of coupled (differential) transmission line analysis."""

    z0_even: float  # even-mode impedance [Ω]
    z0_odd: float  # odd-mode impedance [Ω]
    z_diff: float  # differential impedance [Ω] = 2 * z0_odd


@dataclass(frozen=True)
class SynthesisResult:
    """Result of single-ended synthesis (target Z0 → trace width)."""

    width: float  # trace width [m]
    z0: float  # achieved impedance [Ω]
    converged: bool


@dataclass(frozen=True)
class DifferentialSynthesisResult:
    """Result of differential synthesis (target Zdiff → width + spacing)."""

    width: float  # trace width [m]
    spacing: float  # edge-to-edge spacing [m]
    z0_even: float  # even-mode impedance [Ω]
    z0_odd: float  # odd-mode impedance [Ω]
    z_diff: float  # differential impedance [Ω]
    converged: bool


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------
def elliptic_integral_ratio(k: float) -> float:
    """
    Ratio K(k)/K'(k) of complete elliptic integrals via the
    arithmetic-geometric mean (AGM) algorithm.

    K(k)  = complete elliptic integral of the first kind
    K'(k) = K(k') where k' = sqrt(1 - k^2)

    Uses Hilberg's approximation for k close to 0 or 1,
    and AGM for intermediate values.
    """
    if k < 0.0 or k > 1.0:
        raise ValueError(f"k must be in [0, 1], got {k}")
    if k == 0.0:
        return 0.0
    if k == 1.0:
        return float("inf")

    kp = math.sqrt(1.0 - k * k)

    if k < 1e-6:
        return math.pi / (2.0 * math.log(2.0 / k))
    if kp < 1e-6:
        return 2.0 * math.log(2.0 / kp) / math.pi

    # AGM: K(k)/K'(k) = pi / (2 * ln(2)) * 1 / ln(2*agm(1,kp)/agm(1,k))
    # Simpler: use the standard AGM approach
    # K(k) = pi / (2 * agm(1, kp))
    # K'(k) = pi / (2 * agm(1, k))
    # ratio = agm(1, k) / agm(1, kp)
    def agm(a: float, b: float) -> float:
        for _ in range(50):
            a, b = (a + b) / 2.0, math.sqrt(a * b)
            if abs(a - b) < 1e-15:
                break
        return a

    return agm(1.0, k) / agm(1.0, kp)


def coth(x: float) -> float:
    """Hyperbolic cotangent."""
    return 1.0 / math.tanh(x)


def sech(x: float) -> float:
    """Hyperbolic secant."""
    return 1.0 / math.cosh(x)


# ---------------------------------------------------------------------------
# Microstrip calculator
# ---------------------------------------------------------------------------
class Microstrip:
    """
    Single-ended microstrip impedance calculator.

    Formulas: Hammerstad & Jensen (1980) — filling factor, effective
    dielectric constant, thickness correction, and Z0 for a homogeneous
    microstrip.

    Wheeler (1977) — initial width estimate for synthesis.
    """

    @staticmethod
    def _effective_er(er: float, u: float) -> float:
        """
        Effective dielectric constant of microstrip.
        Hammerstad-Jensen formula.

        er: substrate relative permittivity
        u:  w/h ratio (width / dielectric height)
        """
        a = (
            1.0
            + (1.0 / 49.0) * math.log((u**4 + (u / 52.0) ** 2) / (u**4 + 0.432))
            + (1.0 / 18.7) * math.log(1.0 + (u / 18.1) ** 3)
        )

        b = 0.564 * ((er - 0.9) / (er + 3.0)) ** 0.053

        er_eff = (er + 1.0) / 2.0 + ((er - 1.0) / 2.0) * (1.0 + 10.0 / u) ** (-a * b)
        return er_eff

    @staticmethod
    def _z0_homogeneous(u: float) -> float:
        """
        Characteristic impedance of microstrip with er=1 (air).
        Hammerstad-Jensen.

        u: w/h ratio
        """
        f_u = 6.0 + (2.0 * math.pi - 6.0) * math.exp(-((30.666 / u) ** 0.7528))
        return (ZF0 / (2.0 * math.pi)) * math.log(
            f_u / u + math.sqrt(1.0 + (2.0 / u) ** 2)
        )

    @staticmethod
    def _thickness_correction(
        u: float, t_over_h: float, er: float
    ) -> tuple[float, float]:
        """
        Correct w/h ratio and er_eff for finite strip thickness.

        Returns (delta_u, delta_er_eff_factor).
        t_over_h: trace thickness / dielectric height
        """
        if t_over_h <= 0.0:
            return 0.0, 0.0

        # Width correction (Hammerstad-Jensen)
        delta_u = (t_over_h / math.pi) * math.log(
            1.0 + (4.0 * math.e) / (t_over_h * (coth(math.sqrt(6.517 * u))) ** 2)
        )

        # Er correction factor
        if u <= 1.0 / (2.0 * math.pi):
            er_corr = -(t_over_h / (1.2 * math.pi)) * math.log(
                1.0 + (4.0 * math.pi * u) / t_over_h
            )
        else:
            er_corr = -(t_over_h / (1.2 * math.pi)) * math.log(1.0 + (2.0 / t_over_h))

        return delta_u, er_corr

    @staticmethod
    def analyse(
        w: float,
        h: float,
        t: float,
        er: float,
    ) -> AnalysisResult:
        """
        Analyse a microstrip: given geometry, compute Z0 and er_eff.

        w:  trace width [m]
        h:  dielectric height [m]
        t:  trace thickness [m]
        er: substrate relative permittivity
        """
        u = w / h
        t_over_h = t / h

        # Thickness corrections
        delta_u, delta_er = Microstrip._thickness_correction(u, t_over_h, er)
        u_eff = u + delta_u

        # Effective dielectric constant
        er_eff = Microstrip._effective_er(er, u_eff)
        er_eff += delta_er * (er - 1.0)  # apply thickness correction to er_eff
        er_eff = max(er_eff, 1.0)

        # Z0
        z0_air = Microstrip._z0_homogeneous(u_eff)
        z0 = z0_air / math.sqrt(er_eff)

        return AnalysisResult(z0=z0, er_eff=er_eff)

    @staticmethod
    def synthesize(
        z0_target: float,
        h: float,
        t: float,
        er: float,
        max_iter: int = 50,
        tol: float = 0.01,
    ) -> SynthesisResult:
        """
        Synthesize trace width for target Z0 using Newton-Raphson.

        z0_target: target characteristic impedance [Ω]
        h:  dielectric height [m]
        t:  trace thickness [m]
        er: substrate relative permittivity

        Returns SynthesisResult with width in [m].
        """
        # Wheeler initial guess
        a = (z0_target / 60.0) * math.sqrt((er + 1.0) / 2.0) + (
            (er - 1.0) / (er + 1.0)
        ) * (0.23 + 0.11 / er)
        b = 60.0 * math.pi * math.pi / (z0_target * math.sqrt(er))

        if a > 1.52:
            # Wide strip
            u = (2.0 / math.pi) * (
                b
                - 1.0
                - math.log(2.0 * b - 1.0)
                + ((er - 1.0) / (2.0 * er)) * (math.log(b - 1.0) + 0.39 - 0.61 / er)
            )
        else:
            u = 8.0 * math.exp(a) / (math.exp(2.0 * a) - 2.0)

        w = u * h

        # Newton-Raphson refinement
        converged = False
        for _ in range(max_iter):
            result = Microstrip.analyse(w, h, t, er)
            error = result.z0 - z0_target

            if abs(error) < tol:
                converged = True
                break

            # Numerical derivative
            dw = w * 1e-4
            if dw < 1e-9:
                dw = 1e-9
            result_plus = Microstrip.analyse(w + dw, h, t, er)
            dz0_dw = (result_plus.z0 - result.z0) / dw

            if abs(dz0_dw) < 1e-20:
                break

            w_new = w - error / dz0_dw
            w = max(w_new, h * 0.01)  # clamp to reasonable minimum

        result = Microstrip.analyse(w, h, t, er)
        return SynthesisResult(width=w, z0=result.z0, converged=converged)


# ---------------------------------------------------------------------------
# Stripline calculator
# ---------------------------------------------------------------------------
class Stripline:
    """
    Single-ended stripline impedance calculator.

    For asymmetric stripline (different distances to top and bottom
    ground planes), uses parallel combination:
        Z0 = 2 / (1/Z0_top + 1/Z0_bot)

    Based on the classic stripline formulas from Wheeler and Cohn.
    """

    @staticmethod
    def _z0_symmetric(w: float, h: float, t: float, er: float) -> float:
        """
        Z0 for symmetric stripline (trace centered between ground planes).

        w: trace width [m]
        h: distance from trace to one ground plane [m]
           (total ground-to-ground spacing b = 2*h)
        t: trace thickness [m]
        er: dielectric constant

        Uses Cohn's elliptic integral formulation with thickness correction.
        """
        if w <= 0 or h <= 0:
            return 1000.0  # return high impedance for degenerate case

        b = 2.0 * h  # total ground plane spacing

        # Effective width correction for finite thickness (Cohn)
        if t > 0 and t < b:
            delta_w = (t / math.pi) * (1.0 - math.log(max(2.0 * t / b, 1e-10)))
        else:
            delta_w = 0.0

        w_eff = w + delta_w

        # Cohn stripline formula: k = sech(π*w_eff/(2*b))
        x = w_eff / (2.0 * b)  # standard parameter = w/(2b)

        if x < 0.5:
            # Narrow strip — use elliptic integrals
            kp = math.tanh(math.pi * x)
            z0 = (ZF0 / (4.0 * math.sqrt(er))) * (1.0 / elliptic_integral_ratio(kp))
        else:
            # Wide strip approximation
            cf = -math.log(math.pi / 2.0) + 1.0 / (2.0 * math.pi) * math.log(
                4.0 * math.pi * x
            )
            z0 = (ZF0 / (4.0 * math.sqrt(er))) / (x + cf / math.pi)

        return z0

    @staticmethod
    def analyse(
        w: float,
        h1: float,
        h2: float,
        t: float,
        er1: float,
        er2: float | None = None,
    ) -> AnalysisResult:
        """
        Analyse asymmetric stripline: given geometry, compute Z0.

        w:   trace width [m]
        h1:  dielectric thickness above trace [m]
        h2:  dielectric thickness below trace [m]
        t:   trace thickness [m]
        er1: dielectric constant above
        er2: dielectric constant below (defaults to er1 if None)
        """
        if er2 is None:
            er2 = er1

        # Parallel combination of two symmetric striplines
        z0_top = Stripline._z0_symmetric(w, h1, t, er1)
        z0_bot = Stripline._z0_symmetric(w, h2, t, er2)

        z0 = 2.0 / (1.0 / z0_top + 1.0 / z0_bot)

        # Effective er from the impedance relationship
        z0_air_top = Stripline._z0_symmetric(w, h1, t, 1.0)
        z0_air_bot = Stripline._z0_symmetric(w, h2, t, 1.0)
        z0_air = 2.0 / (1.0 / z0_air_top + 1.0 / z0_air_bot)
        er_eff = (z0_air / z0) ** 2

        return AnalysisResult(z0=z0, er_eff=er_eff)

    @staticmethod
    def synthesize(
        z0_target: float,
        h1: float,
        h2: float,
        t: float,
        er1: float,
        er2: float | None = None,
        max_iter: int = 50,
        tol: float = 0.01,
    ) -> SynthesisResult:
        """
        Synthesize trace width for target Z0 using Newton-Raphson.

        z0_target: target impedance [Ω]
        h1, h2: dielectric thicknesses [m]
        t: trace thickness [m]
        er1, er2: dielectric constants
        """
        if er2 is None:
            er2 = er1

        er_avg = (er1 * h1 + er2 * h2) / (h1 + h2)
        h_total = h1 + h2

        # Initial guess: approximate symmetric stripline formula inverted
        # Z0 ≈ (60/sqrt(er)) * ln(4*h/(0.67*(0.8*w+t)))
        # Solving for w: w ≈ (4*h / (0.67 * exp(Z0*sqrt(er)/60)) - t) / 0.8
        arg = z0_target * math.sqrt(er_avg) / 60.0
        w = max((4.0 * h_total / (0.67 * math.exp(arg)) - t) / 0.8, h_total * 0.05)

        converged = False
        for _ in range(max_iter):
            result = Stripline.analyse(w, h1, h2, t, er1, er2)
            error = result.z0 - z0_target

            if abs(error) < tol:
                converged = True
                break

            dw = w * 1e-4
            if dw < 1e-9:
                dw = 1e-9
            result_plus = Stripline.analyse(w + dw, h1, h2, t, er1, er2)
            dz0_dw = (result_plus.z0 - result.z0) / dw

            if abs(dz0_dw) < 1e-20:
                break

            w_new = w - error / dz0_dw
            w = max(w_new, h_total * 0.01)

        result = Stripline.analyse(w, h1, h2, t, er1, er2)
        return SynthesisResult(width=w, z0=result.z0, converged=converged)


# ---------------------------------------------------------------------------
# Coupled Microstrip calculator
# ---------------------------------------------------------------------------
class CoupledMicrostrip:
    """
    Coupled (differential) microstrip impedance calculator.

    Even/odd mode analysis using Kirschning & Jansen (1984)
    Q-coefficient formulas.

    Zdiff = 2 * Z0_odd
    """

    @staticmethod
    def _even_odd_er(
        er: float, u: float, g: float, er_eff_single: float
    ) -> tuple[float, float]:
        """
        Even and odd mode effective dielectric constants.
        Kirschning-Jansen Q-coefficient formulas.

        er: substrate permittivity
        u:  w/h ratio
        g:  s/h ratio (spacing / height)
        er_eff_single: single-line effective er at this u
        """
        # Even mode
        v = u * (20.0 + g * g) / (10.0 + g * g) + g * math.exp(-g)
        ae = (
            1.0
            + (1.0 / 49.0) * math.log((v**4 + (v / 52.0) ** 2) / (v**4 + 0.432))
            + (1.0 / 18.7) * math.log(1.0 + (v / 18.1) ** 3)
        )
        be = 0.564 * ((er - 0.9) / (er + 3.0)) ** 0.053
        er_eff_even = 0.5 * (er + 1.0) + 0.5 * (er - 1.0) * (1.0 + 10.0 / v) ** (
            -ae * be
        )

        # Odd mode
        ao = 0.7287 * (er_eff_single - 0.5 * (er + 1.0)) * (1.0 - math.exp(-0.179 * g))
        bo = (0.747 * er) / (0.15 + er)
        co = bo - (bo - 0.207) * math.exp(-0.414 * g)
        do = 0.593 + 0.694 * math.exp(-0.562 * g)

        er_eff_odd = (
            0.5 * (er + 1.0) + ao - 0.5 * (er - 1.0) * (1.0 + 10.0 / u) ** (-co * do)
        )

        return er_eff_even, er_eff_odd

    @staticmethod
    def _even_odd_z0(
        u: float, g: float, z0_single: float, er: float
    ) -> tuple[float, float]:
        """
        Even and odd mode impedances.
        Kirschning-Jansen Q-coefficient formulas.

        u:  w/h ratio
        g:  s/h ratio
        z0_single: single-line Z0 (in air or with er) at this u
        er: substrate permittivity (used for Q coefficients)
        """
        # Even mode Q-coefficients
        q1 = 0.8695 * u**0.194
        q2 = 1.0 + 0.7519 * g + 0.189 * g**2.31
        q3 = (
            0.1975
            + (16.6 + (8.4 / g) ** 6) ** (-0.387)
            + math.log(g**10 / (1.0 + (g / 3.4) ** 10)) / 241.0
        )
        q4 = (2.0 * q1 / q2) / (
            math.exp(-g) * u**q3 + (2.0 - math.exp(-g)) * u ** (-q3)
        )

        z0_even_air = (
            z0_single
            * math.sqrt(Microstrip._effective_er(er, u))
            / (1.0 - z0_single * q4 * math.sqrt(Microstrip._effective_er(er, u)) / ZF0)
        )

        # Odd mode Q-coefficients
        q5 = 1.794 + 1.14 * math.log(1.0 + 0.638 / (g + 0.517 * g**2.43))
        q6 = (
            0.2305
            + math.log(g**10 / (1.0 + (g / 5.8) ** 10)) / 281.3
            + math.log(1.0 + 0.598 * g**1.154) / 5.1
        )
        q7 = (10.0 + 190.0 * g * g) / (1.0 + 82.3 * g * g * g)
        q8 = math.exp(-6.5 - 0.95 * math.log(g) - (g / 0.15) ** 5)
        q9 = math.log(q7) * (q8 + 1.0 / 16.5)
        q10 = q2 * q4 - q5 * math.exp(math.log(u) * q6 * u ** (-q9))

        z0_odd_air = (
            z0_single
            * math.sqrt(Microstrip._effective_er(er, u))
            / (1.0 - z0_single * q10 * math.sqrt(Microstrip._effective_er(er, u)) / ZF0)
        )

        return z0_even_air, z0_odd_air

    @staticmethod
    def analyse(
        w: float,
        s: float,
        h: float,
        t: float,
        er: float,
    ) -> DifferentialAnalysisResult:
        """
        Analyse coupled microstrip: given geometry, compute even/odd mode Z0.

        w:  trace width [m]
        s:  edge-to-edge spacing [m]
        h:  dielectric height [m]
        t:  trace thickness [m]
        er: substrate permittivity
        """
        u = w / h
        g = s / h
        t_over_h = t / h

        # Thickness correction for each trace (same as single microstrip)
        delta_u, delta_er = Microstrip._thickness_correction(u, t_over_h, er)
        u_eff = u + delta_u

        # Single-line parameters at effective u
        er_eff_single = Microstrip._effective_er(er, u_eff)
        er_eff_single += delta_er * (er - 1.0)
        er_eff_single = max(er_eff_single, 1.0)

        z0_single_air = Microstrip._z0_homogeneous(u_eff)
        # z0_single = z0_single_air / math.sqrt(er_eff_single)

        # Even/odd effective dielectric constants
        er_eff_even, er_eff_odd = CoupledMicrostrip._even_odd_er(
            er, u_eff, g, er_eff_single
        )
        er_eff_even = max(er_eff_even, 1.0)
        er_eff_odd = max(er_eff_odd, 1.0)

        # Even/odd impedances (in air)
        z0_even_air, z0_odd_air = CoupledMicrostrip._even_odd_z0(
            u_eff, g, z0_single_air, er
        )

        # Apply dielectric
        z0_even = z0_even_air / math.sqrt(er_eff_even)
        z0_odd = z0_odd_air / math.sqrt(er_eff_odd)

        return DifferentialAnalysisResult(
            z0_even=z0_even,
            z0_odd=z0_odd,
            z_diff=2.0 * z0_odd,
        )

    @staticmethod
    def synthesize_fix_spacing(
        z_diff_target: float,
        s: float,
        h: float,
        t: float,
        er: float,
        max_iter: int = 50,
        tol: float = 0.1,
    ) -> DifferentialSynthesisResult:
        """
        Synthesize trace width for target Zdiff with fixed spacing.

        z_diff_target: target differential impedance [Ω]
        s:  fixed edge-to-edge spacing [m]
        h:  dielectric height [m]
        t:  trace thickness [m]
        er: substrate permittivity
        """
        # Initial guess from single-ended synthesis at Z0 = Zdiff/2
        single = Microstrip.synthesize(z_diff_target / 2.0, h, t, er)
        w = single.width

        converged = False
        for _ in range(max_iter):
            result = CoupledMicrostrip.analyse(w, s, h, t, er)
            error = result.z_diff - z_diff_target

            if abs(error) < tol:
                converged = True
                break

            dw = w * 1e-4
            if dw < 1e-9:
                dw = 1e-9
            result_plus = CoupledMicrostrip.analyse(w + dw, s, h, t, er)
            dz_dw = (result_plus.z_diff - result.z_diff) / dw

            if abs(dz_dw) < 1e-20:
                break

            w_new = w - error / dz_dw
            w = max(w_new, h * 0.01)

        result = CoupledMicrostrip.analyse(w, s, h, t, er)
        return DifferentialSynthesisResult(
            width=w,
            spacing=s,
            z0_even=result.z0_even,
            z0_odd=result.z0_odd,
            z_diff=result.z_diff,
            converged=converged,
        )


# ---------------------------------------------------------------------------
# Coupled Stripline calculator
# ---------------------------------------------------------------------------
class CoupledStripline:
    """
    Coupled (differential) stripline impedance calculator.

    Based on S.B. Cohn (1954/1955) elliptic integral formulation with
    fringe capacitance correction for finite strip thickness.

    Zdiff = 2 * Z0_odd
    """

    @staticmethod
    def _coupled_stripline_z0(
        w: float,
        s: float,
        h: float,
        t: float,
        er: float,
    ) -> tuple[float, float]:
        """
        Even/odd mode impedances for coupled stripline using
        Cohn's elliptic integral method.

        w: trace width [m]
        s: edge-to-edge spacing [m]
        h: total ground-to-ground spacing [m] (trace assumed centered)
        t: trace thickness [m]
        er: dielectric constant
        """
        if w <= 0 or h <= 0 or s <= 0:
            return 100.0, 25.0

        b = h  # ground plane spacing

        # Thickness correction: effective width
        if t > 0 and t < b:
            delta_w = (t / math.pi) * (1.0 - math.log(max(2.0 * t / b, 1e-10)))
        else:
            delta_w = 0.0

        w_eff = w + delta_w

        # Even mode: k_even = tanh(pi*w_eff/(2*b)) / tanh(pi*(w_eff+s)/(2*b))
        # Odd mode:  k_odd  = tanh(pi*w_eff/(2*b)) * tanh(pi*(w_eff+s)/(2*b))
        # But we use the complementary form for the impedance.

        arg_w = math.pi * w_eff / (2.0 * b)
        arg_ws = math.pi * (w_eff + s) / (2.0 * b)

        # Clamp to avoid overflow
        arg_w = min(arg_w, 20.0)
        arg_ws = min(arg_ws, 20.0)

        th_w = math.tanh(arg_w)
        th_ws = math.tanh(arg_ws)

        # Even mode
        if th_ws > 1e-10:
            k_even = th_w / th_ws
        else:
            k_even = 0.999

        # Odd mode
        k_odd = th_w * th_ws

        # Clamp k values
        k_even = max(min(k_even, 0.99999), 0.00001)
        k_odd = max(min(k_odd, 0.99999), 0.00001)

        # Z0 = (ZF0 / (4 * sqrt(er))) * K'(k) / K(k) =
        # (ZF0 / (4 * sqrt(er))) / (K(k)/K'(k))
        ratio_even = elliptic_integral_ratio(k_even)
        ratio_odd = elliptic_integral_ratio(k_odd)

        if ratio_even > 1e-10:
            z0_even = (ZF0 / (4.0 * math.sqrt(er))) / ratio_even
        else:
            z0_even = 1000.0

        if ratio_odd > 1e-10:
            z0_odd = (ZF0 / (4.0 * math.sqrt(er))) / ratio_odd
        else:
            z0_odd = 1000.0

        # Fringe capacitance correction for finite thickness
        if t > 0 and t < b:
            cf = (2.0 / math.pi) * math.log(2.0 * b / (math.pi * t) + 1.0)
            # The fringe capacitance reduces impedance slightly
            # Correction factor applied to both modes
            c_corr_even = 1.0 + cf * t / (w_eff * er)
            c_corr_odd = 1.0 + cf * t / (w_eff * er)
            z0_even /= math.sqrt(max(c_corr_even, 1.0))
            z0_odd /= math.sqrt(max(c_corr_odd, 1.0))

        return z0_even, z0_odd

    @staticmethod
    def analyse(
        w: float,
        s: float,
        h1: float,
        h2: float,
        t: float,
        er1: float,
        er2: float | None = None,
    ) -> DifferentialAnalysisResult:
        """
        Analyse coupled stripline.

        w:   trace width [m]
        s:   edge-to-edge spacing [m]
        h1:  dielectric thickness above trace [m]
        h2:  dielectric thickness below trace [m]
        t:   trace thickness [m]
        er1: dielectric constant above
        er2: dielectric constant below (defaults to er1)
        """
        if er2 is None:
            er2 = er1

        h_total = h1 + h2 + t
        er_avg = (er1 * h1 + er2 * h2) / (h1 + h2)

        z0_even, z0_odd = CoupledStripline._coupled_stripline_z0(
            w, s, h_total, t, er_avg
        )

        return DifferentialAnalysisResult(
            z0_even=z0_even,
            z0_odd=z0_odd,
            z_diff=2.0 * z0_odd,
        )

    @staticmethod
    def synthesize_fix_spacing(
        z_diff_target: float,
        s: float,
        h1: float,
        h2: float,
        t: float,
        er1: float,
        er2: float | None = None,
        max_iter: int = 100,
        tol: float = 0.1,
    ) -> DifferentialSynthesisResult:
        """
        Synthesize trace width for target Zdiff with fixed spacing.

        Uses damped Newton-Raphson (max 10% step size).
        """
        if er2 is None:
            er2 = er1

        # Initial guess from single-ended stripline
        single = Stripline.synthesize(z_diff_target / 2.0, h1, h2, t, er1, er2)
        w = single.width

        converged = False
        for _ in range(max_iter):
            result = CoupledStripline.analyse(w, s, h1, h2, t, er1, er2)
            error = result.z_diff - z_diff_target

            if abs(error) < tol:
                converged = True
                break

            dw = w * 1e-4
            if dw < 1e-9:
                dw = 1e-9
            result_plus = CoupledStripline.analyse(w + dw, s, h1, h2, t, er1, er2)
            dz_dw = (result_plus.z_diff - result.z_diff) / dw

            if abs(dz_dw) < 1e-20:
                break

            step = -error / dz_dw
            # Damped: max 10% change per iteration
            max_step = w * 0.1
            if abs(step) > max_step:
                step = math.copysign(max_step, step)

            w = max(w + step, (h1 + h2) * 0.01)

        result = CoupledStripline.analyse(w, s, h1, h2, t, er1, er2)
        return DifferentialSynthesisResult(
            width=w,
            spacing=s,
            z0_even=result.z0_even,
            z0_odd=result.z0_odd,
            z_diff=result.z_diff,
            converged=converged,
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestMicrostrip:
    """Roundtrip tests for Microstrip calculator."""

    def test_synthesize_analyse_50ohm(self):
        """Synthesize 50Ω, analyse back, verify Z0 matches."""
        h = 0.069e-3  # 69 µm prepreg (like JLC040811_1080 outer)
        t = 0.035e-3  # 35 µm copper
        er = 3.91

        result = Microstrip.synthesize(50.0, h, t, er)
        assert result.converged, f"Synthesis did not converge, got Z0={result.z0:.2f}"
        assert abs(result.z0 - 50.0) < 0.1, f"Z0={result.z0:.2f}, expected 50.0"

        # Verify with analyse
        check = Microstrip.analyse(result.width, h, t, er)
        assert abs(check.z0 - 50.0) < 0.1, f"Analysis Z0={check.z0:.2f}, expected 50.0"

    def test_synthesize_analyse_75ohm(self):
        """Synthesize 75Ω, analyse back, verify Z0 matches."""
        h = 0.2e-3
        t = 0.035e-3
        er = 4.5

        result = Microstrip.synthesize(75.0, h, t, er)
        assert result.converged
        assert abs(result.z0 - 75.0) < 0.1

        check = Microstrip.analyse(result.width, h, t, er)
        assert abs(check.z0 - 75.0) < 0.1

    def test_width_increases_with_lower_impedance(self):
        """Lower target impedance should give wider trace."""
        h = 0.1e-3
        t = 0.035e-3
        er = 4.0

        r50 = Microstrip.synthesize(50.0, h, t, er)
        r75 = Microstrip.synthesize(75.0, h, t, er)
        assert r50.width > r75.width


class TestStripline:
    """Roundtrip tests for Stripline calculator."""

    def test_synthesize_analyse_50ohm_symmetric(self):
        """Synthesize 50Ω symmetric stripline."""
        h = 0.25e-3  # 250 µm each side
        t = 0.030e-3
        er = 4.48

        result = Stripline.synthesize(50.0, h, h, t, er)
        assert result.converged, f"Synthesis did not converge, got Z0={result.z0:.2f}"
        assert abs(result.z0 - 50.0) < 0.1, f"Z0={result.z0:.2f}, expected 50.0"

    def test_synthesize_analyse_50ohm_asymmetric(self):
        """Synthesize 50Ω asymmetric stripline (like JLC 4-layer inner)."""
        h1 = 0.069e-3  # prepreg side
        h2 = 0.5e-3  # core side
        t = 0.030e-3
        er1 = 3.91
        er2 = 4.48

        result = Stripline.synthesize(50.0, h1, h2, t, er1, er2)
        assert result.converged
        assert abs(result.z0 - 50.0) < 0.5, f"Z0={result.z0:.2f}, expected 50.0"


class TestCoupledMicrostrip:
    """Roundtrip tests for CoupledMicrostrip calculator."""

    def test_synthesize_analyse_100ohm(self):
        """Synthesize 100Ω differential, analyse back."""
        h = 0.069e-3
        t = 0.035e-3
        er = 3.91
        s = 0.09e-3  # ~3.5 mil spacing

        result = CoupledMicrostrip.synthesize_fix_spacing(100.0, s, h, t, er)
        assert result.converged, (
            f"Synthesis did not converge, got Zdiff={result.z_diff:.2f}"
        )
        assert abs(result.z_diff - 100.0) < 0.5, (
            f"Zdiff={result.z_diff:.2f}, expected 100.0"
        )

    def test_synthesize_analyse_90ohm(self):
        """Synthesize 90Ω differential."""
        h = 0.1e-3
        t = 0.035e-3
        er = 4.0
        s = 0.15e-3

        result = CoupledMicrostrip.synthesize_fix_spacing(90.0, s, h, t, er)
        assert result.converged
        assert abs(result.z_diff - 90.0) < 0.5


class TestCoupledStripline:
    """Roundtrip tests for CoupledStripline calculator."""

    def test_synthesize_analyse_100ohm(self):
        """Synthesize 100Ω differential stripline."""
        h1 = 0.069e-3
        h2 = 0.5e-3
        t = 0.030e-3
        er1 = 3.91
        er2 = 4.48
        s = 0.09e-3

        result = CoupledStripline.synthesize_fix_spacing(100.0, s, h1, h2, t, er1, er2)
        assert result.converged, (
            f"Synthesis did not converge, got Zdiff={result.z_diff:.2f}"
        )
        assert abs(result.z_diff - 100.0) < 1.0, (
            f"Zdiff={result.z_diff:.2f}, expected 100.0"
        )

    def test_synthesize_analyse_100ohm_symmetric(self):
        """Synthesize 100Ω differential symmetric stripline."""
        h = 0.25e-3
        t = 0.030e-3
        er = 4.48
        s = 0.15e-3

        result = CoupledStripline.synthesize_fix_spacing(100.0, s, h, h, t, er)
        assert result.converged
        assert abs(result.z_diff - 100.0) < 1.0
