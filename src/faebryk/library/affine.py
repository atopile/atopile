# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
"""
Affine arithmetic computation module.

Affine forms represent uncertainty about a single unknown value:
    x = x₀ + Σ(cᵢ × εᵢ) ± δ

where:
    x₀ = center (nominal value)
    cᵢ = coefficient for noise symbol εᵢ
    εᵢ ∈ [-1, 1] are noise symbols (shared across forms for correlation)
    δ ≥ 0 = accumulated non-linear approximation error

Shared εᵢ between affine forms enforce that correlated parameters
(e.g. the same resistor appearing in numerator and denominator)
evaluate at the SAME point — unlike standard interval arithmetic
which treats every occurrence independently.

All functions operate on plain Python values (center, terms dict, delta)
extracted from graph node attributes.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import faebryk.core.faebrykpy as fbrk
    import faebryk.core.graph as graph


# ──────────────────────────────────────────────────────────────────────────────
# Types
# ──────────────────────────────────────────────────────────────────────────────

# An affine form in pure-Python representation:
#   (center, {eps_id: coefficient, ...}, delta)
AffineData = tuple[float, dict[int, float], float]


# ──────────────────────────────────────────────────────────────────────────────
# Epsilon allocator
# ──────────────────────────────────────────────────────────────────────────────


class EpsilonAllocator:
    """Assigns unique epsilon IDs. Reuses IDs for the same parameter identity."""

    def __init__(self) -> None:
        self._next_id = 0
        self._param_map: dict[int, int] = {}  # param object id → eps_id

    def get_or_create(self, param_id: int) -> int:
        """Get or create an epsilon ID for a parameter identity."""
        if param_id not in self._param_map:
            self._param_map[param_id] = self._fresh()
        return self._param_map[param_id]

    def _fresh(self) -> int:
        eid = self._next_id
        self._next_id += 1
        return eid

    def fresh(self) -> int:
        """Allocate a fresh epsilon ID (for non-linear error terms)."""
        return self._fresh()


# ──────────────────────────────────────────────────────────────────────────────
# Helper: linear radius of an affine form
# ──────────────────────────────────────────────────────────────────────────────


def _linear_radius(terms: dict[int, float]) -> float:
    """Sum of absolute coefficients: Σ|cᵢ|"""
    return sum(abs(c) for c in terms.values())


def outer_range(af: AffineData) -> tuple[float, float]:
    """Guaranteed superset of the true range of the affine form."""
    center, terms, delta = af
    r = _linear_radius(terms) + delta
    return (center - r, center + r)


def inner_range(af: AffineData) -> tuple[float, float] | None:
    """Guaranteed subset of the true range, or None if delta overwhelms.

    The inner range is valid only when delta < linear_radius, meaning
    the linear terms dominate the non-linear error.
    """
    center, terms, delta = af
    lr = _linear_radius(terms)
    if lr == 0:
        if delta == 0:
            # Singleton
            return (center, center)
        return None
    if delta >= lr:
        return None
    r = lr - delta
    return (center - r, center + r)


# ──────────────────────────────────────────────────────────────────────────────
# Affine arithmetic operations
# ──────────────────────────────────────────────────────────────────────────────


def _merge_terms(
    a_terms: dict[int, float], b_terms: dict[int, float], sign: float = 1.0
) -> dict[int, float]:
    """Merge two term dicts, adding coefficients for shared epsilon IDs."""
    result = dict(a_terms)
    for eid, coeff in b_terms.items():
        result[eid] = result.get(eid, 0.0) + sign * coeff
    # Remove zero terms
    return {k: v for k, v in result.items() if v != 0.0}


def affine_add(a: AffineData, b: AffineData) -> AffineData:
    """Exact affine addition: z = x + y"""
    ac, at, ad = a
    bc, bt, bd = b
    return (ac + bc, _merge_terms(at, bt, 1.0), ad + bd)


def affine_negate(a: AffineData) -> AffineData:
    """Exact affine negation: z = -x"""
    ac, at, ad = a
    return (-ac, {k: -v for k, v in at.items()}, ad)


def affine_subtract(a: AffineData, b: AffineData) -> AffineData:
    """Exact affine subtraction: z = x - y"""
    return affine_add(a, affine_negate(b))


def affine_scalar_multiply(a: AffineData, s: float) -> AffineData:
    """Exact scalar multiplication: z = s * x"""
    ac, at, ad = a
    return (s * ac, {k: s * v for k, v in at.items()}, abs(s) * ad)


def affine_multiply(
    a: AffineData, b: AffineData, alloc: EpsilonAllocator
) -> AffineData:
    """Affine multiplication: z = x * y

    If one operand is a constant (no terms, zero delta), this is exact.
    Otherwise, introduces a new delta term for the non-linear remainder.
    """
    ac, at, ad = a
    bc, bt, bd = b

    # If a is a constant scalar
    if not at and ad == 0.0:
        return affine_scalar_multiply(b, ac)
    # If b is a constant scalar
    if not bt and bd == 0.0:
        return affine_scalar_multiply(a, bc)

    # General case:
    # z₀ = x₀ * y₀
    center = ac * bc

    # Linear terms: z_i = x₀*y_i + y₀*x_i (preserves ε correlation)
    terms: dict[int, float] = {}
    for eid, coeff in at.items():
        terms[eid] = terms.get(eid, 0.0) + bc * coeff
    for eid, coeff in bt.items():
        terms[eid] = terms.get(eid, 0.0) + ac * coeff
    terms = {k: v for k, v in terms.items() if v != 0.0}

    # Non-linear error bound:
    # δ_z = r_x*r_y + |x₀|*δ_y + |y₀|*δ_x + r_x*δ_y + δ_x*r_y + δ_x*δ_y
    rx = _linear_radius(at)
    ry = _linear_radius(bt)
    delta = rx * ry + abs(ac) * bd + abs(bc) * ad + rx * bd + ad * ry + ad * bd

    return (center, terms, delta)


def affine_reciprocal(a: AffineData, alloc: EpsilonAllocator) -> AffineData | None:
    """Affine reciprocal: z = 1/x using optimal secant linearization.

    Returns None if the interval spans zero.
    """
    lo, hi = outer_range(a)
    if lo <= 0 <= hi:
        return None  # interval contains zero

    # Secant linearization of f(x) = 1/x on [lo, hi]
    # Slope: α = -1/(lo*hi)
    alpha = -1.0 / (lo * hi)

    # Optimal intercept to minimize max error
    # For 1/x, the Chebyshev linearization gives:
    # β = (√hi + √lo)² / (2*lo*hi) for positive intervals
    # Error: δ = (√hi - √lo)² / (2*lo*hi)
    if lo > 0:
        sqrt_lo = math.sqrt(lo)
        sqrt_hi = math.sqrt(hi)
    else:
        # Both negative — use |hi| < |lo|
        sqrt_lo = math.sqrt(-hi)
        sqrt_hi = math.sqrt(-lo)

    ac, at, ad = a

    # z₀ = α*x₀ + β where β is chosen for min-max error
    beta = (sqrt_lo + sqrt_hi) ** 2 / (2.0 * abs(lo * hi))
    if lo < 0:
        beta = -beta
    center = alpha * ac + beta

    # Linear terms: z_i = α * x_i
    terms = {k: alpha * v for k, v in at.items()}
    terms = {k: v for k, v in terms.items() if v != 0.0}

    # Non-linear error: from linearization + propagated delta
    lin_delta = (sqrt_hi - sqrt_lo) ** 2 / (2.0 * abs(lo * hi))
    # Additional error from input delta
    # |1/x| has max derivative 1/lo² on [lo, hi] (for positive)
    if lo > 0:
        max_deriv = 1.0 / (lo * lo)
    else:
        max_deriv = 1.0 / (hi * hi)
    delta = lin_delta + max_deriv * ad

    return (center, terms, delta)


def affine_power(a: AffineData, n: int, alloc: EpsilonAllocator) -> AffineData | None:
    """Affine integer power: z = x^n using Chebyshev linearization.

    Handles:
    - n=0: returns 1
    - n=1: returns a
    - n=-1: returns reciprocal
    - n>1: Chebyshev linearization of x^n
    - n<-1: chains power and reciprocal
    """
    if n == 0:
        return (1.0, {}, 0.0)
    if n == 1:
        return a
    if n == -1:
        return affine_reciprocal(a, alloc)
    if n < -1:
        pos = affine_power(a, -n, alloc)
        if pos is None:
            return None
        return affine_reciprocal(pos, alloc)

    # n >= 2: Chebyshev linearization of f(x) = x^n on [lo, hi]
    lo, hi = outer_range(a)

    if lo == hi:
        # Singleton
        val = lo**n
        return (val, {}, 0.0)

    # Chebyshev linearization: slope α from derivative at Chebyshev points
    # For x^n, use min-range affine approximation
    # α = (f(hi) - f(lo)) / (hi - lo)  (secant slope)
    f_lo = lo**n
    f_hi = hi**n
    alpha = (f_hi - f_lo) / (hi - lo)

    # Find the point where f'(x) = α, i.e., n*x^(n-1) = α
    # x* = (α/n)^(1/(n-1))
    ac, at, ad = a

    # For even n with interval crossing zero, just use secant
    # For the intercept, minimize the max error
    mid = (lo + hi) / 2.0
    f_mid = mid**n
    beta_secant = (f_lo + f_hi) / 2.0 - alpha * (lo + hi) / 2.0

    # Compute max error with secant approximation
    # Sample several points to find maximum error
    center = alpha * ac + beta_secant

    # Linear terms
    terms = {k: alpha * v for k, v in at.items()}
    terms = {k: v for k, v in terms.items() if v != 0.0}

    # Error bound: max |f(x) - α*x - β| over [lo, hi]
    # Check at endpoints and critical point where f'(x) = α
    errors = [
        abs(f_lo - alpha * lo - beta_secant),
        abs(f_hi - alpha * hi - beta_secant),
    ]

    if n >= 2 and alpha / n > 0:
        x_crit = (alpha / n) ** (1.0 / (n - 1))
        if lo <= x_crit <= hi:
            f_crit = x_crit**n
            errors.append(abs(f_crit - alpha * x_crit - beta_secant))
        if n % 2 == 0 and lo <= -x_crit <= hi:
            f_crit = (-x_crit) ** n
            errors.append(abs(f_crit - alpha * (-x_crit) - beta_secant))

    lin_delta = max(errors)

    # Additional error from input delta
    # Max derivative of x^n on [lo, hi]
    if lo >= 0:
        max_deriv = abs(n) * hi ** (n - 1)
    elif hi <= 0:
        max_deriv = abs(n) * abs(lo) ** (n - 1)
    else:
        max_deriv = abs(n) * max(abs(lo), abs(hi)) ** (n - 1)

    delta = lin_delta + max_deriv * ad

    return (center, terms, delta)


def affine_sin(a: AffineData, alloc: EpsilonAllocator) -> AffineData:
    """Affine sine: z = sin(x) using secant linearization."""
    lo, hi = outer_range(a)
    ac, at, ad = a

    if lo == hi:
        return (math.sin(lo), {}, 0.0)

    # If range > 2π, output is [-1, 1]
    if hi - lo >= 2 * math.pi:
        return (0.0, {}, 1.0)

    # Secant linearization of sin(x) on [lo, hi]
    f_lo = math.sin(lo)
    f_hi = math.sin(hi)
    alpha = (f_hi - f_lo) / (hi - lo)

    beta = (f_lo + f_hi) / 2.0 - alpha * (lo + hi) / 2.0
    center = alpha * ac + beta

    terms = {k: alpha * v for k, v in at.items()}
    terms = {k: v for k, v in terms.items() if v != 0.0}

    # Error bound: max |sin(x) - α*x - β| over [lo, hi]
    # sin has max deviation 1 from any line, but we can be tighter
    # Sample critical points (where cos(x) = α)
    from faebryk.library.Literals import NumericInterval

    sin_lo, sin_hi = NumericInterval.sine_on_interval((lo, hi))
    lin_lo = alpha * lo + beta
    lin_hi = alpha * hi + beta
    lin_min = min(lin_lo, lin_hi)
    lin_max = max(lin_lo, lin_hi)

    errors = [
        abs(sin_hi - lin_max) if sin_hi > lin_max else 0,
        abs(sin_lo - lin_min) if sin_lo < lin_min else 0,
        abs(f_lo - lin_lo),
        abs(f_hi - lin_hi),
    ]

    lin_delta = max(errors) if errors else 0.0
    # Cap at 1.0 since sin is bounded
    lin_delta = min(lin_delta, 1.0)

    delta = lin_delta + ad  # sin has max derivative 1

    return (center, terms, delta)


def affine_log(a: AffineData, alloc: EpsilonAllocator) -> AffineData | None:
    """Affine natural log: z = ln(x) using secant linearization.

    Returns None if the interval includes non-positive values.
    """
    lo, hi = outer_range(a)
    if lo <= 0:
        return None

    ac, at, ad = a

    if lo == hi:
        return (math.log(lo), {}, 0.0)

    # Secant linearization of ln(x) on [lo, hi]
    f_lo = math.log(lo)
    f_hi = math.log(hi)
    alpha = (f_hi - f_lo) / (hi - lo)

    beta = (f_lo + f_hi) / 2.0 - alpha * (lo + hi) / 2.0
    center = alpha * ac + beta

    terms = {k: alpha * v for k, v in at.items()}
    terms = {k: v for k, v in terms.items() if v != 0.0}

    # Error bound: max |ln(x) - α*x - β| over [lo, hi]
    # Critical point where 1/x = α → x = 1/α
    errors = [abs(f_lo - alpha * lo - beta), abs(f_hi - alpha * hi - beta)]
    x_crit = 1.0 / alpha if alpha > 0 else None
    if x_crit and lo <= x_crit <= hi:
        errors.append(abs(math.log(x_crit) - alpha * x_crit - beta))

    lin_delta = max(errors)
    # Additional error from input delta: max |1/x| on [lo, hi] = 1/lo
    delta = lin_delta + ad / lo

    return (center, terms, delta)


def affine_abs(a: AffineData, alloc: EpsilonAllocator) -> AffineData:
    """Affine absolute value: z = |x|"""
    lo, hi = outer_range(a)
    ac, at, ad = a

    if lo >= 0:
        # Already non-negative
        return a
    if hi <= 0:
        # All negative, just negate
        return affine_negate(a)

    # Crosses zero — linearize |x| on [lo, hi]
    # Secant from lo to hi: slope = (hi - (-lo))/(hi - lo) = (hi+lo)/(hi-lo)... wait
    # |lo| = -lo (since lo < 0), |hi| = hi
    alpha = (hi - (-lo)) / (hi - lo)  # = (hi + lo) / (hi - lo)
    # Intercept that minimizes error
    f_lo = -lo
    f_hi = hi
    beta = (f_lo + f_hi) / 2.0 - alpha * (lo + hi) / 2.0

    center = alpha * ac + beta
    terms = {k: alpha * v for k, v in at.items()}
    terms = {k: v for k, v in terms.items() if v != 0.0}

    # Max error at x=0: |0 - (α*0 + β)| = |β|
    errors = [
        abs(f_lo - alpha * lo - beta),
        abs(f_hi - alpha * hi - beta),
        abs(beta),  # error at x=0
    ]
    lin_delta = max(errors)
    delta = lin_delta + ad

    return (center, terms, delta)


def affine_round(a: AffineData, alloc: EpsilonAllocator) -> AffineData:
    """Affine round: z = round(x)

    Rounding is highly non-linear. We use a conservative approach:
    just compute the interval and use that as a constant + delta.
    """
    lo, hi = outer_range(a)
    r_lo = round(lo)
    r_hi = round(hi)
    center = (r_lo + r_hi) / 2.0
    delta = (r_hi - r_lo) / 2.0
    return (center, {}, delta)


# ──────────────────────────────────────────────────────────────────────────────
# Graph node construction helper
# ──────────────────────────────────────────────────────────────────────────────


def make_affine_form_node(
    center: float,
    terms: dict[int, float],
    delta: float,
    g: "graph.GraphView",
    tg: "fbrk.TypeGraph",
) -> "AffineForm":
    """Create an AffineForm + AffineTerm graph nodes."""
    from faebryk.library.Literals import AffineForm, AffineTerm, AffineTermAttributes

    af = AffineForm.bind_typegraph(tg).create_instance(
        g=g,
        attributes=AffineForm.Attributes(center=center, delta=delta),
    )
    for eps_id, coeff in terms.items():
        term = AffineTerm.bind_typegraph(tg).create_instance(
            g=g,
            attributes=AffineTermAttributes(epsilon_id=eps_id, coefficient=coeff),
        )
        af.terms.get().append(term)
    return af


def extract_affine_data(af: "AffineForm") -> AffineData:
    """Extract pure-Python affine data from an AffineForm graph node."""
    center = af.get_center()
    delta = af.get_delta()
    terms = af.get_terms()
    return (center, terms, delta)
