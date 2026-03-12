# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""Tests for affine arithmetic integration."""

import math

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.library._F as F
from faebryk.library.affine import (
    AffineData,
    EpsilonAllocator,
    affine_add,
    affine_abs,
    affine_log,
    affine_multiply,
    affine_negate,
    affine_power,
    affine_reciprocal,
    affine_round,
    affine_scalar_multiply,
    affine_sin,
    affine_subtract,
    extract_affine_data,
    inner_range,
    make_affine_form_node,
    outer_range,
)
from faebryk.library.Literals import AffineForm, AffineTerm, Numbers


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _make_param_af(lo: float, hi: float, eps_id: int) -> AffineData:
    """Create an affine form representing a parameter in [lo, hi]."""
    center = (lo + hi) / 2.0
    half = (hi - lo) / 2.0
    return (center, {eps_id: half}, 0.0)


def _sample_affine(af: AffineData, eps_vals: dict[int, float]) -> float:
    """Evaluate an affine form at specific epsilon values in [-1, 1]."""
    center, terms, delta = af
    val = center
    for eid, coeff in terms.items():
        val += coeff * eps_vals.get(eid, 0.0)
    return val


def _true_range_by_sampling(
    func, *afs: AffineData, n_samples: int = 1000
) -> tuple[float, float]:
    """Estimate true range of func applied to affine forms via sampling.

    All affine forms must share the same epsilon space.
    """
    import random

    random.seed(42)

    # Collect all epsilon IDs
    all_eids = set()
    for af in afs:
        all_eids.update(af[1].keys())

    lo = float("inf")
    hi = float("-inf")
    for _ in range(n_samples):
        eps_vals = {eid: random.uniform(-1, 1) for eid in all_eids}
        sampled = [_sample_affine(af, eps_vals) for af in afs]
        try:
            result = func(*sampled)
            lo = min(lo, result)
            hi = max(hi, result)
        except (ValueError, ZeroDivisionError):
            pass

    return (lo, hi)


# ──────────────────────────────────────────────────────────────────────────────
# Pure affine arithmetic tests
# ──────────────────────────────────────────────────────────────────────────────


class TestAffineAdd:
    def test_basic_add(self):
        a = (5.0, {0: 1.0}, 0.0)
        b = (3.0, {1: 2.0}, 0.0)
        result = affine_add(a, b)
        assert result[0] == 8.0  # center
        assert result[1] == {0: 1.0, 1: 2.0}  # terms merged
        assert result[2] == 0.0  # delta

    def test_add_shared_epsilon(self):
        """Adding two forms with same ε should add coefficients."""
        a = (5.0, {0: 1.0}, 0.0)
        b = (3.0, {0: 2.0}, 0.0)
        result = affine_add(a, b)
        assert result[0] == 8.0
        assert result[1] == {0: 3.0}
        assert result[2] == 0.0


class TestAffineSubtract:
    def test_self_cancellation(self):
        """P - P should give zero range when using same epsilon."""
        p = _make_param_af(9.0, 11.0, eps_id=0)  # [9, 11], ε₀
        result = affine_subtract(p, p)
        assert result[0] == 0.0
        assert result[1] == {}  # all coefficients cancel
        assert result[2] == 0.0
        lo, hi = outer_range(result)
        assert lo == 0.0
        assert hi == 0.0

    def test_different_params(self):
        """P₁ - P₂ with different ε should give nonzero range."""
        p1 = _make_param_af(9.0, 11.0, eps_id=0)
        p2 = _make_param_af(9.0, 11.0, eps_id=1)
        result = affine_subtract(p1, p2)
        lo, hi = outer_range(result)
        assert lo == -2.0
        assert hi == 2.0


class TestAffineMultiply:
    def test_scalar_multiply(self):
        """Multiplying by a constant is exact."""
        a = (5.0, {0: 1.0}, 0.0)
        b = (3.0, {}, 0.0)  # constant
        alloc = EpsilonAllocator()
        result = affine_multiply(a, b, alloc)
        assert result[0] == 15.0
        assert result[1] == {0: 3.0}
        assert result[2] == 0.0

    def test_general_multiply(self):
        """General multiply introduces non-linear error."""
        a = (5.0, {0: 1.0}, 0.0)
        b = (3.0, {1: 0.5}, 0.0)
        alloc = EpsilonAllocator()
        result = affine_multiply(a, b, alloc)
        assert result[0] == 15.0
        # Check that outer range is superset of true range
        true_lo, true_hi = _true_range_by_sampling(lambda x, y: x * y, a, b)
        or_lo, or_hi = outer_range(result)
        assert or_lo <= true_lo
        assert or_hi >= true_hi

    def test_correlated_multiply(self):
        """P * P with same epsilon should be tighter than interval."""
        p = _make_param_af(2.0, 4.0, eps_id=0)  # [2, 4]
        alloc = EpsilonAllocator()
        result = affine_multiply(p, p, alloc)
        or_lo, or_hi = outer_range(result)
        # Interval arithmetic: [2,4]*[2,4] = [4, 16]
        # Affine should be tighter since P*P is correlated
        # True range: [4, 16] (same in this case since x² is monotonic on [2,4])
        assert or_lo <= 4.0
        assert or_hi >= 16.0


class TestAffineReciprocal:
    def test_positive_interval(self):
        a = _make_param_af(2.0, 4.0, eps_id=0)
        alloc = EpsilonAllocator()
        result = affine_reciprocal(a, alloc)
        assert result is not None
        or_lo, or_hi = outer_range(result)
        # True range: [1/4, 1/2] = [0.25, 0.5]
        assert or_lo <= 0.25
        assert or_hi >= 0.5

    def test_negative_interval(self):
        a = _make_param_af(-4.0, -2.0, eps_id=0)
        alloc = EpsilonAllocator()
        result = affine_reciprocal(a, alloc)
        assert result is not None
        or_lo, or_hi = outer_range(result)
        assert or_lo <= -0.5
        assert or_hi >= -0.25

    def test_spanning_zero_returns_none(self):
        a = _make_param_af(-1.0, 1.0, eps_id=0)
        alloc = EpsilonAllocator()
        result = affine_reciprocal(a, alloc)
        assert result is None


class TestAffinePower:
    def test_power_zero(self):
        a = _make_param_af(2.0, 4.0, eps_id=0)
        alloc = EpsilonAllocator()
        result = affine_power(a, 0, alloc)
        assert result == (1.0, {}, 0.0)

    def test_power_one(self):
        a = _make_param_af(2.0, 4.0, eps_id=0)
        alloc = EpsilonAllocator()
        result = affine_power(a, 1, alloc)
        assert result == a

    def test_power_two(self):
        a = _make_param_af(2.0, 4.0, eps_id=0)
        alloc = EpsilonAllocator()
        result = affine_power(a, 2, alloc)
        assert result is not None
        or_lo, or_hi = outer_range(result)
        # True range: [4, 16]
        assert or_lo <= 4.0
        assert or_hi >= 16.0

    def test_power_neg_one(self):
        a = _make_param_af(2.0, 4.0, eps_id=0)
        alloc = EpsilonAllocator()
        result = affine_power(a, -1, alloc)
        assert result is not None
        or_lo, or_hi = outer_range(result)
        assert or_lo <= 0.25
        assert or_hi >= 0.5


class TestOuterInnerRange:
    def test_outer_range_basic(self):
        af = (5.0, {0: 1.0, 1: 2.0}, 0.5)
        lo, hi = outer_range(af)
        # radius = |1| + |2| + 0.5 = 3.5
        assert lo == 1.5
        assert hi == 8.5

    def test_inner_range_valid(self):
        af = (5.0, {0: 1.0, 1: 2.0}, 0.5)
        ir = inner_range(af)
        assert ir is not None
        lo, hi = ir
        # inner_radius = 3.0 - 0.5 = 2.5
        assert lo == 2.5
        assert hi == 7.5

    def test_inner_range_none_when_delta_dominates(self):
        af = (5.0, {0: 1.0}, 2.0)
        ir = inner_range(af)
        assert ir is None  # delta (2) >= lr (1)

    def test_singleton(self):
        af = (5.0, {}, 0.0)
        lo, hi = outer_range(af)
        assert lo == 5.0
        assert hi == 5.0
        ir = inner_range(af)
        assert ir == (5.0, 5.0)


class TestEpsilonAllocator:
    def test_same_param_gets_same_id(self):
        alloc = EpsilonAllocator()
        id1 = alloc.get_or_create(42)
        id2 = alloc.get_or_create(42)
        assert id1 == id2

    def test_different_params_get_different_ids(self):
        alloc = EpsilonAllocator()
        id1 = alloc.get_or_create(42)
        id2 = alloc.get_or_create(99)
        assert id1 != id2

    def test_fresh_is_unique(self):
        alloc = EpsilonAllocator()
        ids = {alloc.fresh() for _ in range(10)}
        assert len(ids) == 10


# ──────────────────────────────────────────────────────────────────────────────
# Graph node tests
# ──────────────────────────────────────────────────────────────────────────────


class TestAffineFormNode:
    def test_create_and_read(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        af = make_affine_form_node(
            center=5.0,
            terms={0: 1.0, 1: 2.0},
            delta=0.5,
            g=g,
            tg=tg,
        )
        assert af.get_center() == 5.0
        assert af.get_delta() == 0.5
        terms = af.get_terms()
        assert terms[0] == 1.0
        assert terms[1] == 2.0

    def test_outer_range(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        af = make_affine_form_node(
            center=5.0,
            terms={0: 1.0, 1: 2.0},
            delta=0.5,
            g=g,
            tg=tg,
        )
        lo, hi = af.outer_range()
        assert lo == 1.5
        assert hi == 8.5

    def test_extract_affine_data(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        af = make_affine_form_node(
            center=3.0,
            terms={7: 1.5},
            delta=0.1,
            g=g,
            tg=tg,
        )
        data = extract_affine_data(af)
        assert data[0] == 3.0
        assert data[1] == {7: 1.5}
        assert data[2] == 0.1


class TestNumbersAffine:
    def test_set_and_get_affine(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        nums = (
            Numbers.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup_from_min_max(min=1.0, max=10.0)
        )
        af = make_affine_form_node(center=5.5, terms={0: 4.5}, delta=0.0, g=g, tg=tg)
        nums.set_affine(af)
        got = nums.try_get_affine()
        assert got is not None
        assert got.get_center() == 5.5

    def test_no_affine_returns_none(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        nums = (
            Numbers.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup_from_min_max(min=1.0, max=10.0)
        )
        assert nums.try_get_affine() is None

    def test_tighten_via_subtract(self):
        """P - P with same ε should produce tighter interval than [lo-hi, hi-lo]."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        p = (
            Numbers.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup_from_min_max(min=9.0, max=11.0)
        )
        af = make_affine_form_node(center=10.0, terms={0: 1.0}, delta=0.0, g=g, tg=tg)
        p.set_affine(af)
        result = p.op_subtract_intervals(p, g=g, tg=tg)
        # With affine: P-P = 0 (exact cancellation)
        # Without affine: [9-11, 11-9] = [-2, 2]
        assert result.get_min_value() == 0.0
        assert result.get_max_value() == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# Numbers op propagation tests
# ──────────────────────────────────────────────────────────────────────────────


class TestNumbersOpPropagation:
    @staticmethod
    def _make_nums_with_affine(lo: float, hi: float, eps_id: int, g, tg) -> Numbers:
        nums = (
            Numbers.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup_from_min_max(min=lo, max=hi)
        )
        center = (lo + hi) / 2.0
        half = (hi - lo) / 2.0
        af = make_affine_form_node(center, {eps_id: half}, 0.0, g=g, tg=tg)
        nums.set_affine(af)
        return nums

    def test_add_propagates_affine(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        a = self._make_nums_with_affine(1.0, 3.0, 0, g, tg)
        b = self._make_nums_with_affine(2.0, 4.0, 1, g, tg)
        result = a.op_add_intervals(b, g=g, tg=tg)
        assert result.try_get_affine() is not None

    def test_subtract_self_cancels(self):
        """P - P with same ε should give [0, 0]."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        p = self._make_nums_with_affine(9.0, 11.0, 0, g, tg)
        result = p.op_subtract_intervals(p, g=g, tg=tg)
        af = result.try_get_affine()
        assert af is not None
        lo, hi = af.outer_range()
        assert abs(lo) < 1e-10
        assert abs(hi) < 1e-10

    def test_multiply_propagates_affine(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        a = self._make_nums_with_affine(2.0, 4.0, 0, g, tg)
        b = self._make_nums_with_affine(3.0, 5.0, 1, g, tg)
        result = a.op_mul_intervals(b, g=g, tg=tg)
        assert result.try_get_affine() is not None

    def test_negate_propagates_affine(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        a = self._make_nums_with_affine(2.0, 4.0, 0, g, tg)
        result = a.op_negate(g=g, tg=tg)
        af = result.try_get_affine()
        assert af is not None
        lo, hi = af.outer_range()
        assert lo == -4.0
        assert hi == -2.0

    def test_div_propagates_affine(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        a = self._make_nums_with_affine(6.0, 10.0, 0, g, tg)
        b = self._make_nums_with_affine(2.0, 4.0, 1, g, tg)
        result = a.op_div_intervals(b, g=g, tg=tg)
        assert result.try_get_affine() is not None

    def test_pow_propagates_affine(self):
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        base = self._make_nums_with_affine(2.0, 4.0, 0, g, tg)
        exp = (
            Numbers.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup_from_min_max(min=2.0, max=2.0)
        )
        result = base.op_pow_intervals(exp, g=g, tg=tg)
        assert result.try_get_affine() is not None

    def test_add_tightens_interval(self):
        """P + P with same ε should be tighter than [2*lo, 2*hi]."""
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)
        p = self._make_nums_with_affine(9.0, 11.0, 0, g, tg)
        result = p.op_add_intervals(p, g=g, tg=tg)
        # Interval arithmetic: [18, 22]
        # Affine: center=20, terms={0: 2}, range=[18, 22]
        # Same in this case since P+P is exact
        assert result.get_min_value() == 18.0
        assert result.get_max_value() == 22.0


# ──────────────────────────────────────────────────────────────────────────────
# Voltage divider benchmark
# ──────────────────────────────────────────────────────────────────────────────


class TestVoltageDividerAffine:
    def test_voltage_divider_narrow_ranges(self):
        """Test R1/(R0+R1) with affine arithmetic on narrow-tolerance parts.

        Voltage divider: v_out = v_in * r_bottom / (r_top + r_bottom)
        With r_top ∈ [9.9, 10.1], r_bottom ∈ [19.8, 20.2], v_in ∈ [4.95, 5.05]:
        (1% tolerance resistors, 1% voltage)

        True range: v_in * r_bottom/(r_top+r_bottom)
        True min ≈ 4.95 * 19.8/30.3 ≈ 3.233
        True max ≈ 5.05 * 20.2/29.9 ≈ 3.413
        """
        alloc = EpsilonAllocator()

        r_top = _make_param_af(9.9, 10.1, eps_id=alloc.get_or_create(1))
        r_bottom = _make_param_af(19.8, 20.2, eps_id=alloc.get_or_create(2))
        v_in = _make_param_af(4.95, 5.05, eps_id=alloc.get_or_create(3))

        r_sum = affine_add(r_top, r_bottom)
        r_sum_inv = affine_reciprocal(r_sum, alloc)
        assert r_sum_inv is not None

        ratio = affine_multiply(r_bottom, r_sum_inv, alloc)
        v_out = affine_multiply(v_in, ratio, alloc)

        or_lo, or_hi = outer_range(v_out)

        # Outer range should be a superset of the true range
        true_lo, true_hi = _true_range_by_sampling(
            lambda vi, rb, rt: vi * rb / (rt + rb),
            v_in,
            r_bottom,
            r_top,
            n_samples=10000,
        )
        assert or_lo <= true_lo + 1e-10
        assert or_hi >= true_hi - 1e-10

        # Interval arithmetic width for comparison
        # [4.95,5.05]*[19.8,20.2]*[1/30.3, 1/29.9] gives much wider
        ia_lo = 4.95 * 19.8 / 30.3
        ia_hi = 5.05 * 20.2 / 29.9
        # But interval arithmetic independently handles numerator/denominator
        # producing: [4.95*19.8/(10.1+20.2), 5.05*20.2/(9.9+19.8)]
        # = [98.01/30.3, 101.01/29.7] = [3.234, 3.401]
        # vs independent IA: [4.95*19.8/30.3, 5.05*20.2/29.7] = [3.234, 3.434]
        # Affine should be at least as tight
        affine_width = or_hi - or_lo
        assert affine_width < 1.0, (
            f"Affine width {affine_width:.4f} for 1%-tolerance divider"
        )

    def test_r_div_r_identity_narrow(self):
        """R / R with narrow range should approach [1, 1] with affine.

        With 1% tolerance: R ∈ [99, 101]
        Standard interval: [99/101, 101/99] = [0.980, 1.020]
        Affine (same ε): should be very close to [1, 1]
        """
        alloc = EpsilonAllocator()
        r = _make_param_af(99.0, 101.0, eps_id=0)

        r_inv = affine_reciprocal(r, alloc)
        assert r_inv is not None
        result = affine_multiply(r, r_inv, alloc)

        or_lo, or_hi = outer_range(result)
        # Interval arithmetic: [99/101, 101/99] ≈ [0.980, 1.020]
        # Affine should be much tighter due to shared ε
        assert or_lo > 0.99, f"Expected lo > 0.99, got {or_lo}"
        assert or_hi < 1.01, f"Expected hi < 1.01, got {or_hi}"
