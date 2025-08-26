# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Iterable

import faebryk.library._F as F
from faebryk.core.link import LinkDirectConditional, LinkDirectConditionalFilterResult
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import CNode, Node
from faebryk.libs.library import L
from faebryk.libs.sets.quantity_sets import Quantity_Interval
from faebryk.libs.units import P


class ElectricSignal(F.Signal):
    """
    ElectricSignal is a class that represents a signal that is represented
    by the voltage between the reference.hv and reference.lv.
    """

    class LinkIsolatedReference(LinkDirectConditional):
        def test(self, node: CNode):
            return not isinstance(node, F.ElectricPower)

        def __init__(self) -> None:
            super().__init__(
                lambda path: LinkDirectConditionalFilterResult.FILTER_PASS
                if all(self.test(dst.node) for dst in path)
                else LinkDirectConditionalFilterResult.FILTER_FAIL_UNRECOVERABLE,
                needs_only_first_in_path=True,
            )

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    line: F.Electrical
    reference: F.ElectricPower

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(self.reference)

    # ----------------------------------------
    #                functions
    # ----------------------------------------
    @staticmethod
    def connect_all_node_references(
        nodes: Iterable[Node], gnd_only=False
    ) -> F.ElectricPower:
        # TODO check if any child contains ElectricLogic which is not connected
        # e.g find them in graph and check if any has parent without "single reference"

        refs = {
            x.get_trait(F.has_single_electric_reference).get_reference()
            for x in nodes
            if x.has_trait(F.has_single_electric_reference)
        } | {x for x in nodes if isinstance(x, F.ElectricPower)}
        assert refs

        if gnd_only:
            F.Electrical.connect(*{r.lv for r in refs})
            return next(iter(refs))

        F.ElectricPower.connect(*refs)

        return next(iter(refs))

    @classmethod
    def connect_all_module_references(
        cls,
        node: Module | ModuleInterface,
        gnd_only=False,
        exclude: Iterable[Node] = (),
    ) -> F.ElectricPower:
        return cls.connect_all_node_references(
            node.get_children(
                direct_only=True, types=(Module, ModuleInterface)
            ).difference(set(exclude)),
            gnd_only=gnd_only,
        )

    @staticmethod
    def connect_all_references(ifs: Iterable["ElectricSignal"]) -> F.ElectricPower:
        return F.ElectricPower.connect(*[x.reference for x in ifs])

    @L.rt_field
    def surge_protected(self):
        class _can_be_surge_protected_defined(F.can_be_surge_protected_defined):
            def protect(_self, owner: Module):
                out = super().protect(owner)
                for tvs in out.get_children(direct_only=False, types=F.TVS):
                    tvs.reverse_working_voltage.alias_is(self.reference.voltage)
                return out

        return _can_be_surge_protected_defined(self.reference.lv, self.line)

    @property
    def pull_resistance(self) -> Quantity_Interval | None:
        if (connected_to := self.line.get_connected()) is None:
            return None

        resistors: list[F.Resistor] = []
        for mif, _ in connected_to.items():
            if (maybe_parent := mif.get_parent()) is None:
                continue
            parent, _ = maybe_parent

            if not isinstance(parent, F.Resistor):
                continue
            other_side = [x for x in parent.unnamed if x is not mif]
            if len(other_side) != 1:
                continue
            if self.reference.hv not in other_side[0].get_connected():
                continue
            resistors.append(parent)

        if len(resistors) == 0:
            return Quantity_Interval.from_center(0 * P.ohm, 0 * P.ohm)
        elif len(resistors) == 1:
            return resistors[0].resistance.try_get_literal_subset()
        else:
            # cannot determine effective resistance of multiple resistors without
            # inspecting circuit topology
            return None

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import ElectricSignal, ElectricPower

        signal = new ElectricSignal

        # Connect power reference for signal levels
        power_3v3 = new ElectricPower
        assert power_3v3.voltage within 3.3V +/- 5%
        signal.reference ~ power_3v3

        # Connect between components
        sensor_output ~ signal.line
        adc_input ~ signal.line

        # For differential signals, use two ElectricSignals
        diff_pos = new ElectricSignal
        diff_neg = new ElectricSignal
        diff_pos.reference ~ power_3v3
        diff_neg.reference ~ power_3v3
        """,
        language=F.has_usage_example.Language.ato,
    )
