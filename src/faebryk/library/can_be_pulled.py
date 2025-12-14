# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F


class can_be_pulled(fabll.Node):
    is_trait = fabll.Traits.MakeEdge((fabll.ImplementsTrait.MakeChild())).put_on_type()

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
        if obj.has_trait(F.has_pulls):
            up_r, down_r = obj.get_trait(F.has_pulls).get_pulls()

        if up and up_r:
            return up_r
        if not up and down_r:
            return down_r

        resistor = F.Resistor.bind_typegraph(self.tg).create_instance(g=self.g)
        name = obj.get_name(accept_no_parent=True)
        # TODO handle collisions
        if up:
            fbrk.EdgeComposition.add_child(
                bound_node=owner.instance,
                child=resistor.instance.node(),
                child_identifier=f"pull_up_{name}",
            )
            up_r = resistor
        else:
            fbrk.EdgeComposition.add_child(
                bound_node=owner.instance,
                child=resistor.instance.node(),
                child_identifier=f"pull_down_{name}",
            )
            down_r = resistor

        resistor.can_bridge.get().bridge(
            self.line,
            self.reference.hv.get() if up else self.reference.lv.get(),
        )

        fabll.Traits.create_and_add_instance_to(node=obj, trait=F.has_pulls).setup(
            up_r, down_r
        )
        return resistor

    @classmethod
    def MakeChild(
        cls: type[Self],
        line: fabll._ChildField[F.Electrical],
        reference: fabll._ChildField[F.ElectricPower],
    ) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Collections.Pointer.MakeEdge(
                [out, cls.line_],
                [line],
            )
        )
        out.add_dependant(
            F.Collections.Pointer.MakeEdge(
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
    def pull_resistance(self) -> F.Parameters.NumericParameter | None:
        """Calculate effective pull resistance between line and reference.hv.
        Returns a NumericParameter aliased to the resolved literal, or None if it
        cannot be derived."""
        if (connected_to := self.line._is_interface.get().get_connected()) is None:
            return None

        parallel_resistors: list[F.Resistor] = []
        for mif, _ in connected_to.items():
            if (maybe_parent := mif.get_parent()) is None:
                continue
            parent, _ = maybe_parent

            if not parent.isinstance(F.Resistor):
                continue

            resistor = F.Resistor.bind_instance(parent.instance)
            other_side = [
                x
                for x in resistor.get_children(
                    direct_only=True, include_root=False, types=F.Electrical
                )
                if not x.is_same(mif)
            ]
            assert len(other_side) == 1, "Resistors are bilateral"

            if (
                self.reference.hv.get()
                not in other_side[0]._is_interface.get().get_connected()
            ):
                # cannot trivially determine effective resistance
                return None

            parallel_resistors.append(resistor)

        if len(parallel_resistors) == 0:
            return None

        resistances: list[F.Literals.Numbers | None] = []
        parameters: list[F.Parameters.NumericParameter] = []
        for resistor in parallel_resistors:
            param = resistor.resistance.get()
            parameters.append(param)
            lit_trait = param.get_trait(
                F.Parameters.is_parameter_operatable
            ).try_get_subset_or_alias_literal()
            resistances.append(
                None if lit_trait is None else fabll.Traits(lit_trait).get_obj_raw()
            )

        if any(r is None for r in resistances):
            # missing resistance information
            return None
        try:  # R_eff = 1 / (1/R1 + 1/R2 + ... + 1/Rn)
            inverse_sum = None
            resistance_literals = [r.cast(F.Literals.Numbers) for r in resistances]  # type: ignore[arg-type]
            for resistance in resistance_literals:
                inv = resistance.op_invert(g=self.g, tg=self.tg)
                inverse_sum = (
                    inv
                    if inverse_sum is None
                    else inverse_sum.op_add_intervals(inv, g=self.g, tg=self.tg)
                )  # type: ignore[arg-type]

            if inverse_sum is None:
                return None

            eff_literal = inverse_sum.op_invert(g=self.g, tg=self.tg).convert_to_unit(
                g=self.g, tg=self.tg, unit=parameters[0].get_units()
            )
            eff_param = (
                F.Parameters.NumericParameter.bind_typegraph(tg=self.tg)
                .create_instance(g=self.g)
                .setup(units=parameters[0].get_units())
            )
            eff_param.alias_to_literal(g=self.g, value=eff_literal)
            return eff_param
        except ZeroDivisionError:
            return None
