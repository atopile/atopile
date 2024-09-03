# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from enum import Enum, auto
from typing import Iterable, Self

import faebryk.library._F as F
from faebryk.core.graphinterface import GraphInterface
from faebryk.core.link import LinkFilteredException, _TLinkDirectShallow
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import Node
from faebryk.libs.library import L


class ElectricLogic(F.SignalElectrical, F.Logic):
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

    class LinkIsolatedReference(_TLinkDirectShallow):
        def __init__(self, interfaces: list[GraphInterface]) -> None:
            if any(isinstance(gif.node, F.ElectricPower) for gif in interfaces):
                raise LinkFilteredException("All nodes are ElectricPower")
            super().__init__(interfaces)

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

    push_pull: F.TBD[PushPull]

    @L.rt_field
    def single_electric_reference(self):
        return F.has_single_electric_reference_defined(self.reference)

    @L.rt_field
    def surge_protected(self):
        class _can_be_surge_protected_defined(F.can_be_surge_protected_defined):
            def protect(_self):
                return [
                    tvs.builder(
                        lambda t: t.reverse_working_voltage.merge(
                            self.reference.voltage
                        )
                    )
                    for tvs in super().protect()
                ]

        return _can_be_surge_protected_defined(self.reference.lv, self.signal)

    @L.rt_field
    def pulled(self):
        return ElectricLogic.can_be_pulled_defined(self.signal, self.reference)

    def connect_to_electric(self, signal: F.Electrical, reference: F.ElectricPower):
        self.reference.connect(reference)
        self.signal.connect(signal)
        return self

    def connect_reference(self, reference: F.ElectricPower, invert: bool = False):
        if invert:
            # TODO
            raise NotImplementedError()
        #    inverted : F.ElectricPower
        #    inverted.lv.connect(reference.hv)
        #    inverted.hv.connect(reference.lv)
        #    reference = inverted
        self.reference.connect(reference)

    def connect_references(self, other: "ElectricLogic", invert: bool = False):
        self.connect_reference(other.reference, invert=invert)

    def set(self, on: bool):
        super().set(on)
        r = self.reference
        self.signal.connect(r.hv if on else r.lv)

    def set_weak(self, on: bool):
        return self.get_trait(self.can_be_pulled).pull(up=on)

    @staticmethod
    def connect_all_references(ifs: Iterable["ElectricLogic"]) -> F.ElectricPower:
        from faebryk.core.util import connect_all_interfaces

        out = connect_all_interfaces([x.reference for x in ifs])
        assert out
        return out

    @staticmethod
    def connect_all_node_references(
        nodes: Iterable[Node], gnd_only=False
    ) -> F.ElectricPower:
        from faebryk.core.util import connect_all_interfaces
        # TODO check if any child contains ElectricLogic which is not connected
        # e.g find them in graph and check if any has parent without "single reference"

        refs = {
            x.get_trait(F.has_single_electric_reference).get_reference()
            for x in nodes
            if x.has_trait(F.has_single_electric_reference)
        } | {x for x in nodes if isinstance(x, F.ElectricPower)}
        assert refs

        if gnd_only:
            connect_all_interfaces({r.lv for r in refs})
            return next(iter(refs))

        connect_all_interfaces(refs)
        return next(iter(refs))

    @classmethod
    def connect_all_module_references(
        cls, node: Module | ModuleInterface, gnd_only=False
    ) -> F.ElectricPower:
        return cls.connect_all_node_references(
            node.get_children(direct_only=True, types=(Module, ModuleInterface)),
            gnd_only=gnd_only,
        )

    # def connect_shallow(self, other: "ElectricLogic"):
    #    self.connect(
    #        other,
    #        linkcls=self.LinkDirectShallowLogic,
    #    )

    def connect_via_bridge(
        self, bridge: Module, up: bool, bridge_ref_to_signal: bool = False
    ):
        target = self.reference.hv if up else self.reference.lv
        if bridge_ref_to_signal:
            return target.connect_via(bridge, self.signal)
        return self.signal.connect_via(bridge, target)

    def connect_shallow(
        self,
        other: Self,
        signal: bool = False,
        reference: bool = False,
        lv: bool = False,
    ) -> Self:
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
