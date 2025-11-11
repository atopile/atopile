# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.node import Node, NodeAttributes


from functools import reduce
from typing import Iterable

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
)
from faebryk.libs.util import cast_assert


class ElectricSignal(fabll.Node):
    """
    ElectricSignal is a class that represents a signal that is represented
    by the voltage between the reference.hv and reference.lv.
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    line = F.Electrical.MakeChild()
    reference = F.ElectricPower.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.is_interface.MakeChild()

    _single_electric_reference = fabll.ChildField(F.has_single_electric_reference)

    @staticmethod
    def connect_all_node_references(
        reference: F.ElectricPower, nodes: Iterable[fabll.Node], gnd_only=False
    ):
        # TODO check if any child contains ElectricLogic which is not connected
        # e.g find them in graph and check if any has parent without "single reference"

        refs = {
            x.get_trait(F.has_single_electric_reference).get_reference()
            for x in nodes
            if x.has_trait(F.has_single_electric_reference)
        } | {x for x in nodes if isinstance(x, F.ElectricPower)}
        assert refs

        if gnd_only:
            reference.lv.get().get_trait(fabll.is_interface).connect_to(
                *{r.lv.get() for r in refs}
            )
        else:
            reference.get_trait(fabll.is_interface).connect_to(*{r for r in refs})

    @classmethod
    def connect_all_module_references(
        cls,
        reference: F.ElectricPower,
        node: fabll.Node,
        ground_only=False,
        exclude: Iterable[fabll.Node] = (),
    ) -> F.ElectricPower:
        return cls.connect_all_node_references(
            node.get_children(
                direct_only=True, types=fabll.Node, required_trait=fabll.is_interface
            ).difference(set[Node[NodeAttributes]](exclude)),
            gnd_only=ground_only,
        )

    @property
    def pull_resistance(self) -> Quantity_Interval | Quantity_Interval_Disjoint | None:
        if (
            connected_to := self.line.get_trait(fabll.is_interface).get_connected()
        ) is None:
            return None

        parallel_resistors: list[F.Resistor] = []
        for mif, _ in connected_to.items():
            if (maybe_parent := mif.get_parent()) is None:
                continue
            parent, _ = maybe_parent

            if not isinstance(parent, F.Resistor):
                continue

            other_side = [x for x in parent.unnamed if x is not mif]
            assert len(other_side) == 1, "Resistors are bilateral"

            if (
                self.reference.hv
                not in other_side[0].get_trait(fabll.is_interface).get_connected()
            ):
                # cannot trivially determine effective resistance
                return None

            parallel_resistors.append(parent)

        if len(parallel_resistors) == 0:
            return Quantity_Interval.from_center(0 * P.ohm, 0 * P.ohm)
        elif len(parallel_resistors) == 1:
            (resistor,) = parallel_resistors
            return resistor.resistance.try_get_literal_subset()
        else:
            resistances = [
                resistor.resistance.try_get_literal_subset()
                for resistor in parallel_resistors
            ]

            if any(r is None for r in resistances):
                # incomplete solution
                return None

            if any(not isinstance(r, Quantity_Interval) for r in resistances):
                # invalid resistance value
                return None

            # R_eff = 1 / (1/R1 + 1/R2 + ... + 1/Rn)
            try:
                return cast_assert(
                    (Quantity_Interval, Quantity_Interval_Disjoint),
                    reduce(
                        lambda a, b: a + b,
                        [
                            cast_assert(Quantity_Interval, r).op_invert()
                            for r in resistances
                        ],
                    ),
                ).op_invert()
            except ZeroDivisionError:
                return None

    usage_example = F.has_usage_example.MakeChild(
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
    ).put_on_type()
