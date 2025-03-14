import faebryk.library._F as F
from faebryk.core.solver.defaultsolver import DefaultSolver
from faebryk.libs.library import L
from faebryk.libs.units import P


def test_lc_filter():
    lowpass = F.FilterElectricalLC()
    lowpass.response.constrain_subset(F.Filter.Response.LOWPASS)
    lowpass.cutoff_frequency.constrain_subset(L.Range.from_center_rel(1 * P.kHz, 0.15))
    lowpass.in_.reference.voltage.constrain_subset(
        L.Range.from_center_rel(3 * P.V, 0.05)
    )
    lowpass.out.reference.voltage.constrain_subset(
        L.Range.from_center_rel(3 * P.V, 0.05)
    )

    solver = DefaultSolver()
    solver.simplify_symbolically(lowpass.get_graph())
    assert (
        solver.inspect_get_known_supersets(lowpass.inductor.inductance) == 100 * P.uH
    )  # TODO: actual value
    assert (
        solver.inspect_get_known_supersets(lowpass.capacitor.capacitance) == 100 * P.nF
    )  # TODO: actual value


def test_rc_filter():
    lowpass = F.FilterElectricalRC()
    lowpass.response.constrain_subset(F.Filter.Response.LOWPASS)
    lowpass.cutoff_frequency.constrain_subset(L.Range.from_center_rel(1 * P.kHz, 0.15))
    lowpass.in_.reference.voltage.constrain_subset(
        L.Range.from_center_rel(3 * P.V, 0.05)
    )
    lowpass.out.reference.voltage.constrain_subset(
        L.Range.from_center_rel(3 * P.V, 0.05)
    )

    solver = DefaultSolver()
    solver.simplify_symbolically(lowpass.get_graph())
    assert (
        solver.inspect_get_known_supersets(lowpass.resistor.resistance) == 100 * P.kohm
    )  # TODO: actual value
    assert (
        solver.inspect_get_known_supersets(lowpass.capacitor.capacitance) == 100 * P.nF
    )  # TODO: actual value
