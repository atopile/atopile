# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from enum import Enum, auto
from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class ElectricLogic(fabll.Node):
    """
    ElectricLogic is a class that represents a logic signal.
    Logic signals only have two states: high and low.
    For more states / continuous signals check ElectricSignal.
    """

    class has_pulls(fabll.Node):
        _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

        up_ = F.Collections.Pointer.MakeChild()
        down_ = F.Collections.Pointer.MakeChild()

        def get_pulls(self) -> tuple[F.Resistor | None, F.Resistor | None]:
            up_node = self.up_.get().deref()
            down_node = self.down_.get().deref()
            up = (
                F.Resistor.bind_instance(up_node.instance)
                if up_node is not None
                else None
            )
            down = (
                F.Resistor.bind_instance(down_node.instance)
                if down_node is not None
                else None
            )
            return up, down

        def setup(self, up: F.Resistor | None, down: F.Resistor | None) -> Self:
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
            if obj.has_trait(ElectricLogic.has_pulls):
                up_r, down_r = obj.get_trait(ElectricLogic.has_pulls).get_pulls()

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

            fabll.Traits.create_and_add_instance_to(
                node=obj, trait=ElectricLogic.has_pulls
            ).setup(up_r, down_r)
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

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    line_ = F.Electrical.MakeChild()
    reference_ = F.ElectricPower.MakeChild()

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_interface = fabll.is_interface.MakeChild()
    _single_electric_reference = fabll.ChildField(F.has_single_electric_reference)

    @property
    def line(self) -> F.Electrical:
        return self.line_.get()

    @property
    def reference(self) -> F.ElectricPower:
        return self.reference_.get()

    class PushPull(Enum):
        PUSH_PULL = auto()
        OPEN_DRAIN = auto()
        OPEN_SOURCE = auto()

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    push_pull_ = F.Parameters.EnumParameter.MakeChild(
        enum_t=PushPull,
    )

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _can_be_pulled = can_be_pulled.MakeChild(line_, reference_)

    # ----------------------------------------
    #                functions
    # ----------------------------------------
    def set(self, on: bool):
        """
        Set the logic signal by directly connecting to the reference.
        """
        r = self.reference
        self.line.get_trait(fabll.is_interface).connect_to(
            r.hv.get() if on else r.lv.get()
        )

    def set_weak(self, on: bool, owner: fabll.Node):
        """
        Set the logic signal by connecting to the reference via a pull resistor.
        """
        return self.get_trait(self.can_be_pulled).pull(up=on, owner=owner)

    def connect_shallow(
        self,
        other: Self,
        signal: bool = False,
        reference: bool = False,
        lv: bool = False,
    ) -> Self:
        # TODO this should actually use shallow links
        assert not (signal and reference)
        assert not (lv and reference)

        # TODO make custom LinkDirectShallow that also allows the specified params
        if signal:
            self.line.get_trait(fabll.is_interface).connect_to(other.line)
        if reference:
            self.reference.get_trait(fabll.is_interface).connect_to(other.reference)
        if lv:
            self.reference.lv.get().get_trait(fabll.is_interface).connect_to(
                other.reference.lv.get()
            )

        self.get_trait(fabll.is_interface).connect_shallow_to(other)

        return self

    usage_example = F.has_usage_example.MakeChild(
        example="""
        import ElectricLogic

        logic_signal = new ElectricLogic

        logic_signal.reference ~ example_electric_power

        logic_signal.line ~ electrical
        # OR
        logic_signal.line ~ electricLogic.line
        # OR
        logic_signal.line ~> example_resistor ~> electrical
        """,
        language=F.has_usage_example.Language.ato,
    ).put_on_type()
