# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import sys
from abc import abstractmethod
from enum import Enum, auto
from typing import Self

import faebryk.library._F as F
from faebryk.libs.library import L


class ElectricLogic(F.SignalElectrical):
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
        def pull(self, up: bool) -> F.Resistor: ...

    class can_be_pulled_defined(can_be_pulled.impl()):
        def __init__(self, signal: F.Electrical, ref: F.ElectricPower) -> None:
            super().__init__()
            self.ref = ref
            self.signal = signal

        def pull(self, up: bool):
            obj = self.obj

            up_r, down_r = None, None
            if obj.has_trait(ElectricLogic.has_pulls):
                up_r, down_r = obj.get_trait(ElectricLogic.has_pulls).get_pulls()

            if up and up_r:
                return up_r
            if not up and down_r:
                return down_r

            resistor = F.Resistor()
            if up:
                obj.add(resistor, "pull_up")
                up_r = resistor
            else:
                obj.add(resistor, "pull_down")
                down_r = resistor

            self.signal.connect_via(resistor, self.ref.hv if up else self.ref.lv)

            obj.add(ElectricLogic.has_pulls_defined(up_r, down_r))
            return resistor

    # class can_be_buffered(Trait):
    #    @abstractmethod
    #    def buffer(self):
    #        ...
    #
    #
    # class can_be_buffered_defined(can_be_buffered.impl()):
    #    def __init__(self, signal: "ElectricLogic") -> None:
    #        super().__init__()
    #        self.signal = signal
    #
    #    def buffer(self):
    #        obj = self.obj
    #
    #        if hasattr(obj, "buffer"):
    #            return cast_assert(SignalBuffer, getattr(obj, "buffer"))
    #
    #        buffer = SignalBuffer()
    #        obj.buffer = buffer
    #        self.signal.connect(buffer.logic_in)
    #
    #        return buffer.logic_out

    class PushPull(Enum):
        PUSH_PULL = auto()
        OPEN_DRAIN = auto()
        OPEN_SOURCE = auto()

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    push_pull: F.TBD

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    @L.rt_field
    def pulled(self):
        return ElectricLogic.can_be_pulled_defined(self.signal, self.reference)

    specializable_types = L.f_field(F.can_specialize_defined)([F.Logic])

    # ----------------------------------------
    #                functions
    # ----------------------------------------
    def set(self, on: bool):
        """
        Set the logic signal by directly connecting to the reference.
        """
        r = self.reference
        self.signal.connect(r.hv if on else r.lv)

    def set_weak(self, on: bool):
        """
        Set the logic signal by connecting to the reference via a pull resistor.
        """
        return self.get_trait(self.can_be_pulled).pull(up=on)

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
            self.signal.connect(other.signal)
        if reference:
            self.reference.connect(other.reference)
        if lv:
            self.reference.lv.connect(other.reference.lv)

        return super().connect_shallow(other)

    def connect(self, *other: Self, linkcls=None):
        recursion_depth = sys.getrecursionlimit()
        sys.setrecursionlimit(10000)
        ret = super().connect(*other, linkcls=linkcls)
        sys.setrecursionlimit(recursion_depth)
        return ret
