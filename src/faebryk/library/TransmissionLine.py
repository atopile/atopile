# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging
from dataclasses import dataclass

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Unit conversion helpers
# ---------------------------------------------------------------------------
def _mm_to_mil(mm: float) -> float:
    return mm / 0.0254


def _mil_to_mm(mil: float) -> float:
    return mil * 0.0254


# ---------------------------------------------------------------------------
#  ResolvedLayer — plain-data snapshot of a PCBLayer
# ---------------------------------------------------------------------------
@dataclass
class ResolvedLayer:
    layer_type: str  # "COPPER", "SUBSTRATE", "CORE"
    thickness_mm: float
    epsilon_r: float | None  # None for copper layers


class is_transmissionline(fabll.Node):
    """
    Marks an ElectricSignal as a transmission line.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def get_electrical_signal(self) -> "F.ElectricSignal":
        return fabll.Traits(self).get_obj_raw().cast(F.ElectricSignal)

    def get_net_name(self) -> str | None:
        from faebryk.libs.nets import get_named_net

        net = get_named_net(self.get_electrical_signal().line.get())
        if net:
            return net.get_name()
        return None

    def get_characteristic_impedance(self) -> F.Literals.Numbers:
        signal = self.get_electrical_signal()
        impedance = signal.characteristic_impedance.get().try_extract_superset()
        if impedance:
            return impedance
        raise ValueError(
            "No characteristic impedance value set for "
            f"{signal.get_name(accept_no_parent=True)}"
        )

    def get_differential_pair(
        self,
    ) -> "F.DifferentialPair | None":
        """
        Get the differential pair if this transmission line is part of a
        differential pair.
        """
        from faebryk.library._F import DifferentialPair

        return self.get_parent_of_type(DifferentialPair)


class TraceCalculator:
    """
    Calculate the trace geometry for a transmission line given:
    - PCB layer stackup
    - trace characteristic or differential impedance

    Generate data to create DRC rules.
    """

    @dataclass
    class TraceGeometry:
        trace_width_mm: float
        trace_spacing_mm: float | None  # differential only
        impedance_ohm: float  # computed impedance (may differ from target)

    @dataclass
    class TraceRule:
        name: str
        net_name: str
        layer: str  # KiCad layer name: "F.Cu", "In1.Cu", etc.
        trace_width_mm: float
        trace_spacing_mm: float | None  # differential only
        impedance_ohm: float

    # ------------------------------------------------------------------
    #  Resolve stackup from faebryk PCBoard node
    # ------------------------------------------------------------------
    @staticmethod
    def resolve_stackup(board: F.PCBManu.PCBoard) -> list[ResolvedLayer]:
        """Extract the PCBLayer children of a PCBoard into plain data."""
        from faebryk.library.PCBManu import PCBLayer

        layers = board.get_children(
            direct_only=True,
            types=PCBLayer,
        )
        resolved: list[ResolvedLayer] = []
        for layer in layers:
            lt_str = layer.layer_type.force_extract_singleton()

            # thickness is stored in base SI units (meters)
            thickness_m = layer.thickness.force_extract_superset().get_single()
            thickness_mm = thickness_m * 1000.0

            epsilon_r: float | None = None
            if lt_str != "COPPER":
                er_lit = layer.epsilon_r.try_extract_superset()
                if er_lit is not None:
                    epsilon_r = er_lit.get_single()

            resolved.append(
                ResolvedLayer(
                    layer_type=lt_str,
                    thickness_mm=thickness_mm,
                    epsilon_r=epsilon_r,
                )
            )
        return resolved

    # ------------------------------------------------------------------
    #  KiCad copper layer naming
    # ------------------------------------------------------------------
    @staticmethod
    def _copper_layer_name(copper_index: int, total_copper: int) -> str:
        if copper_index == 0:
            return "F.Cu"
        if copper_index == total_copper - 1:
            return "B.Cu"
        return f"In{copper_index}.Cu"

    # ------------------------------------------------------------------
    #  Core calculation — works on resolved (plain) data
    # ------------------------------------------------------------------
    @staticmethod
    def calculate_for_stackup(
        stackup: list[ResolvedLayer],
        impedance_ohm: float,
        net_name: str,
        is_differential: bool = False,
        min_spacing_mm: float = 0.09,
    ) -> list[TraceCalculator.TraceRule]:
        """Calculate trace rules for every copper layer in *stackup*.

        Uses local transmission line formulas (Hammerstad-Jensen,
        Kirschning-Jansen, Cohn) — no network access required.
        """
        from faebryk.libs.transline_calculations import (
            CoupledMicrostrip,
            CoupledStripline,
            Microstrip,
            Stripline,
        )

        copper_indices = [
            i for i, layer in enumerate(stackup) if layer.layer_type == "COPPER"
        ]
        total_copper = len(copper_indices)

        trace_rules: list[TraceCalculator.TraceRule] = []

        for copper_num, stackup_idx in enumerate(copper_indices):
            is_outer = (
                stackup_idx == copper_indices[0] or stackup_idx == copper_indices[-1]
            )

            # Copper thickness (mm → m)
            t_m = stackup[stackup_idx].thickness_mm * 1e-3

            layer_name = TraceCalculator._copper_layer_name(copper_num, total_copper)

            if is_outer:
                # ----- Microstrip -----
                if stackup_idx == copper_indices[0]:
                    ref_idx = copper_indices[1]
                    dielectric_range = range(stackup_idx + 1, ref_idx)
                else:
                    ref_idx = copper_indices[-2]
                    dielectric_range = range(ref_idx + 1, stackup_idx)

                h_mm, er = _sum_dielectric(stackup, dielectric_range)
                h_m = h_mm * 1e-3

                if is_differential:
                    s_m = min_spacing_mm * 1e-3
                    result = CoupledMicrostrip.synthesize_fix_spacing(
                        impedance_ohm, s_m, h_m, t_m, er
                    )
                    trace_rules.append(
                        TraceCalculator.TraceRule(
                            name=f"impedance_{net_name}_{layer_name}",
                            net_name=net_name,
                            layer=layer_name,
                            trace_width_mm=result.width * 1e3,
                            trace_spacing_mm=min_spacing_mm,
                            impedance_ohm=result.z_diff,
                        )
                    )
                else:
                    result = Microstrip.synthesize(impedance_ohm, h_m, t_m, er)
                    trace_rules.append(
                        TraceCalculator.TraceRule(
                            name=f"impedance_{net_name}_{layer_name}",
                            net_name=net_name,
                            layer=layer_name,
                            trace_width_mm=result.width * 1e3,
                            trace_spacing_mm=None,
                            impedance_ohm=result.z0,
                        )
                    )
            else:
                # ----- Stripline -----
                copper_pos = copper_indices.index(stackup_idx)
                ref_above = copper_indices[copper_pos - 1]
                ref_below = copper_indices[copper_pos + 1]

                h1_mm, er1 = _sum_dielectric(stackup, range(ref_above + 1, stackup_idx))
                h2_mm, er2 = _sum_dielectric(stackup, range(stackup_idx + 1, ref_below))
                h1_m = h1_mm * 1e-3
                h2_m = h2_mm * 1e-3

                if is_differential:
                    s_m = min_spacing_mm * 1e-3
                    result = CoupledStripline.synthesize_fix_spacing(
                        impedance_ohm, s_m, h1_m, h2_m, t_m, er1, er2
                    )
                    trace_rules.append(
                        TraceCalculator.TraceRule(
                            name=f"impedance_{net_name}_{layer_name}",
                            net_name=net_name,
                            layer=layer_name,
                            trace_width_mm=result.width * 1e3,
                            trace_spacing_mm=min_spacing_mm,
                            impedance_ohm=result.z_diff,
                        )
                    )
                else:
                    result = Stripline.synthesize(
                        impedance_ohm, h1_m, h2_m, t_m, er1, er2
                    )
                    trace_rules.append(
                        TraceCalculator.TraceRule(
                            name=f"impedance_{net_name}_{layer_name}",
                            net_name=net_name,
                            layer=layer_name,
                            trace_width_mm=result.width * 1e3,
                            trace_spacing_mm=None,
                            impedance_ohm=result.z0,
                        )
                    )

        return trace_rules

    # ------------------------------------------------------------------
    #  High-level entry point (faebryk nodes)
    # ------------------------------------------------------------------
    def calculate_trace_geometry(
        self,
        transmission_line: is_transmissionline,
        board_spec: F.PCBManu.PCBoard,
    ) -> list[TraceRule]:
        stackup = self.resolve_stackup(board_spec)
        diff_pair = transmission_line.get_differential_pair()
        net_name = transmission_line.get_net_name() or "unknown"

        if diff_pair is not None:
            impedance_lit = (
                diff_pair.differential_impedance.get().try_extract_superset()
            )
            if impedance_lit is None:
                raise ValueError(
                    "No differential impedance set on "
                    f"{diff_pair.get_name(accept_no_parent=True)}"
                )
            impedance_ohm = impedance_lit.get_single()
        else:
            impedance_ohm = (
                transmission_line.get_characteristic_impedance().get_single()
            )

        return self.calculate_for_stackup(
            stackup=stackup,
            impedance_ohm=impedance_ohm,
            net_name=net_name,
            is_differential=diff_pair is not None,
        )


# ---------------------------------------------------------------------------
#  Internal helper: sum dielectric thickness + weighted-average epsilon_r
# ---------------------------------------------------------------------------
def _sum_dielectric(
    stackup: list[ResolvedLayer],
    idx_range: range,
) -> tuple[float, float]:
    """Return (total_thickness_mm, weighted_average_epsilon_r)."""
    h_mm = 0.0
    er_sum = 0.0
    for i in idx_range:
        h_mm += stackup[i].thickness_mm
        er_sum += stackup[i].thickness_mm * (stackup[i].epsilon_r or 4.0)
    er_avg = er_sum / h_mm if h_mm > 0 else 4.0
    return h_mm, er_avg


class TestTransmissionLine:
    def test_bus_parameter(self):
        from faebryk.core.solver.solver import Solver

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class App(fabll.Node):
            e1 = F.ElectricSignal.MakeChild()
            e2 = F.ElectricSignal.MakeChild()

            _constraints = [
                F.Literals.Numbers.MakeChild_SetSingleton(
                    [
                        e1,
                        F.ElectricSignal.characteristic_impedance,
                    ],
                    90.0,
                    unit=F.Units.Ohm,
                ),
            ]
            _connections = [
                fabll.is_interface.MakeConnectionEdge(
                    [e1],
                    [e2],
                ),
            ]

        app = App.bind_typegraph(tg).create_instance(g=g)

        # resolve bus parameters
        F.is_alias_bus_parameter.resolve_bus_parameters(g=g, tg=tg)
        solver = Solver()
        solver.simplify(g=g, tg=tg)

        impedance_e1 = solver.extract_superset(
            app.e1.get()
            .characteristic_impedance.get()
            .is_parameter_operatable.get()
            .as_parameter.force_get()
        )
        impedance_e2 = solver.extract_superset(
            app.e1.get()
            .characteristic_impedance.get()
            .is_parameter_operatable.get()
            .as_parameter.force_get()
        )
        assert impedance_e1.pretty_str() == impedance_e2.pretty_str()
        assert impedance_e1.switch_cast().get_single() == 90.0


class TestTraceCalculator:
    """Tests for TraceCalculator (offline, uses local calculators)."""

    # JLC040811_1080 stackup: 4-layer 0.8mm with 1080 prepreg
    JLC040811_1080 = [
        ResolvedLayer("COPPER", 0.035, None),
        ResolvedLayer("SUBSTRATE", 0.069, 3.91),
        ResolvedLayer("COPPER", 0.03, None),
        ResolvedLayer("CORE", 0.5, 4.48),
        ResolvedLayer("COPPER", 0.03, None),
        ResolvedLayer("SUBSTRATE", 0.069, 3.91),
        ResolvedLayer("COPPER", 0.035, None),
    ]

    def test_single_ended_50ohm_4layer(self):
        rules = TraceCalculator.calculate_for_stackup(
            stackup=self.JLC040811_1080,
            impedance_ohm=50.0,
            net_name="test_net",
            is_differential=False,
        )

        assert len(rules) == 4
        assert rules[0].layer == "F.Cu"
        assert rules[1].layer == "In1.Cu"
        assert rules[2].layer == "In2.Cu"
        assert rules[3].layer == "B.Cu"

        for rule in rules:
            width_mil = _mm_to_mil(rule.trace_width_mm)
            assert 3 <= width_mil <= 15, (
                f"Unexpected width {width_mil:.1f} mil on {rule.layer}"
            )
            assert rule.trace_spacing_mm is None
            assert rule.net_name == "test_net"

        # Outer layers (microstrip) should be symmetric
        assert abs(rules[0].trace_width_mm - rules[3].trace_width_mm) < 0.001

        # Inner layers (stripline) should be symmetric
        assert abs(rules[1].trace_width_mm - rules[2].trace_width_mm) < 0.001

    def test_differential_100ohm_4layer(self):
        rules = TraceCalculator.calculate_for_stackup(
            stackup=self.JLC040811_1080,
            impedance_ohm=100.0,
            net_name="usb_dp",
            is_differential=True,
        )

        assert len(rules) == 4
        for rule in rules:
            width_mil = _mm_to_mil(rule.trace_width_mm)
            assert 2 <= width_mil <= 15, (
                f"Unexpected width {width_mil:.1f} mil on {rule.layer}"
            )
            assert rule.trace_spacing_mm is not None

    def test_copper_layer_naming(self):
        assert TraceCalculator._copper_layer_name(0, 4) == "F.Cu"
        assert TraceCalculator._copper_layer_name(1, 4) == "In1.Cu"
        assert TraceCalculator._copper_layer_name(2, 4) == "In2.Cu"
        assert TraceCalculator._copper_layer_name(3, 4) == "B.Cu"
        assert TraceCalculator._copper_layer_name(0, 6) == "F.Cu"
        assert TraceCalculator._copper_layer_name(5, 6) == "B.Cu"
