# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from enum import Enum, auto
from typing import Self

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L


class ElectricLogic(F.ElectricSignal):
    """
    ElectricLogic is a class that represents a logic signal.
    Logic signals only have two states: high and low.
    For more states / continuous signals check ElectricSignal.
    """

    class has_pulls(F.Logic.TraitT):
        @abstractmethod
        def get_pulls(self) -> tuple[F.Resistor | None, F.Resistor | None]: ...

    class has_pulls_defined(has_pulls.impl()):
        def __init__(self, up: F.Resistor | None, down: F.Resistor | None) -> None:
            super().__init__()
            self.up = up
            self.down = down

        def get_pulls(self) -> tuple[F.Resistor | None, F.Resistor | None]:
            return self.up, self.down

    class can_be_pulled(F.Logic.TraitT):
        @abstractmethod
        def pull(self, up: bool, owner: Module) -> F.Resistor: ...

    class can_be_pulled_defined(can_be_pulled.impl()):
        def __init__(self, line: F.Electrical, ref: F.ElectricPower) -> None:
            super().__init__()
            self.ref = ref
            self.line = line

        def pull(self, up: bool, owner: Module):
            obj = self.obj

            up_r, down_r = None, None
            if obj.has_trait(ElectricLogic.has_pulls):
                up_r, down_r = obj.get_trait(ElectricLogic.has_pulls).get_pulls()

            if up and up_r:
                return up_r
            if not up and down_r:
                return down_r

            resistor = F.Resistor()
            name = obj.get_name(accept_no_parent=True)
            # TODO handle collisions
            if up:
                owner.add(resistor, f"pull_up_{name}")
                up_r = resistor
            else:
                owner.add(resistor, f"pull_down_{name}")
                down_r = resistor

            self.line.connect_via(resistor, self.ref.hv if up else self.ref.lv)

            obj.add(ElectricLogic.has_pulls_defined(up_r, down_r))
            return resistor

    # class can_be_buffered(Trait):
    #    @abstractmethod
    #    def buffer(self):
    #        ...
    #
    #
    # class can_be_buffered_defined(can_be_buffered.impl()):
    #    def __init__(self, line: "ElectricLogic") -> None:
    #        super().__init__()
    #        self.line = line
    #
    #    def buffer(self):
    #        obj = self.obj
    #
    #        if hasattr(obj, "buffer"):
    #            return cast_assert(SignalBuffer, getattr(obj, "buffer"))
    #
    #        buffer = SignalBuffer()
    #        obj.buffer = buffer
    #        self.line.connect(buffer.logic_in)
    #
    #        return buffer.logic_out

    class PushPull(Enum):
        PUSH_PULL = auto()
        OPEN_DRAIN = auto()
        OPEN_SOURCE = auto()

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    push_pull = L.p_field(
        domain=L.Domains.ENUM(PushPull),
    )

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    @L.rt_field
    def pulled(self):
        return ElectricLogic.can_be_pulled_defined(self.line, self.reference)

    specializable_types = L.f_field(F.can_specialize_defined)([F.Logic])

    # ----------------------------------------
    #                functions
    # ----------------------------------------
    def set(self, on: bool):
        """
        Set the logic signal by directly connecting to the reference.
        """
        r = self.reference
        self.line.connect(r.hv if on else r.lv)

    def set_weak(self, on: bool, owner: Module):
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
            self.line.connect(other.line)
        if reference:
            self.reference.connect(other.reference)
        if lv:
            self.reference.lv.connect(other.reference.lv)

        return super().connect_shallow(other)

    usage_example = L.f_field(F.has_usage_example)(
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
    )
