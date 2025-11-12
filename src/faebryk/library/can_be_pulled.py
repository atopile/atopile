# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self
from functools import reduce

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.sets.quantity_sets import (
    Quantity_Interval,
    Quantity_Interval_Disjoint,
)
from faebryk.libs.units import P
from faebryk.libs.util import cast_assert


class has_pulls(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    up_ = F.Collections.Pointer.MakeChild()
    down_ = F.Collections.Pointer.MakeChild()

    def get_pulls(self) -> tuple["F.Resistor | None", "F.Resistor | None"]:
        up_node = self.up_.get().deref()
        down_node = self.down_.get().deref()
        up = F.Resistor.bind_instance(up_node.instance) if up_node is not None else None
        down = (
            F.Resistor.bind_instance(down_node.instance)
            if down_node is not None
            else None
        )
        return up, down

    def setup(self, up: "F.Resistor | None", down: "F.Resistor | None") -> Self:
        if up is not None:
            self.up_.get().point(up)
        if down is not None:
            self.down_.get().point(down)
        return self


class can_be_pulled(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    reference_ = F.Collections.Pointer.MakeChild()
    line_ = F.Collections.Pointer.MakeChild()

    @property
    def reference(self) -> F.ElectricPower:
        return F.ElectricPower.bind_instance(self.reference_.get().deref().instance)

    @property
    def line(self) -> F.Electrical:
        return F.Electrical.bind_instance(self.line_.get().deref().instance)

    def pull(self, up: bool, owner: fabll.Node):
        obj = self.get_parent_force()[0]

        up_r, down_r = None, None
        if obj.has_trait(has_pulls):
            up_r, down_r = obj.get_trait(has_pulls).get_pulls()

        if up and up_r:
            return up_r
        if not up and down_r:
            return down_r

        resistor = F.Resistor.bind_typegraph(self.tg).create_instance(
            g=self.tg.get_graph_view()
        )
        name = obj.get_name(accept_no_parent=True)
        # TODO handle collisions
        if up:
            fabll.EdgeComposition.add_child(
                bound_node=owner.instance,
                child=resistor.instance.node(),
                child_identifier=f"pull_up_{name}",
            )
            up_r = resistor
        else:
            fabll.EdgeComposition.add_child(
                bound_node=owner.instance,
                child=resistor.instance.node(),
                child_identifier=f"pull_down_{name}",
            )
            down_r = resistor

        resistor._can_bridge.get().bridge(
            self.line,
            self.reference.hv.get() if up else self.reference.lv.get(),
        )

        fabll.Traits.create_and_add_instance_to(node=obj, trait=has_pulls).setup(
            up_r, down_r
        )
        return resistor

    @classmethod
    def MakeChild(
        cls: type[Self],
        line: fabll.ChildField[F.Electrical],
        reference: fabll.ChildField[F.ElectricPower],
    ) -> fabll.ChildField:
        out = fabll.ChildField(cls)
        out.add_dependant(
            F.Collections.Pointer.EdgeField(
                [out, cls.line_],
                [line],
            )
        )
        out.add_dependant(
            F.Collections.Pointer.EdgeField(
                [out, cls.reference_],
                [reference],
            )
        )
        return out

    def setup(self, line: F.Electrical, reference: F.ElectricPower) -> Self:
        self.reference_.get().point(reference)
        self.line_.get().point(line)
        return self

    @property
    def pull_resistance(self):
        """Calculate the effective pull resistance by finding parallel resistors
        connected between the line and the reference power rail."""
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
