# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from typing import Iterable, Self

from faebryk.core.core import (
    Module,
    ModuleInterface,
    Node,
    NodeTrait,
)
from faebryk.core.util import connect_all_interfaces
from faebryk.library.can_be_surge_protected_defined import (
    can_be_surge_protected_defined,
)
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_single_electric_reference import has_single_electric_reference
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.Logic import Logic
from faebryk.library.Resistor import Resistor


class ElectricLogic(Logic):
    class has_pulls(NodeTrait):
        @abstractmethod
        def get_pulls(self) -> tuple[Resistor | None, Resistor | None]:
            ...

    class has_pulls_defined(has_pulls.impl()):
        def __init__(self, up: Resistor | None, down: Resistor | None) -> None:
            super().__init__()
            self.up = up
            self.down = down

        def get_pulls(self) -> tuple[Resistor | None, Resistor | None]:
            return self.up, self.down

    class can_be_pulled(NodeTrait):
        @abstractmethod
        def pull(self, up: bool) -> Resistor:
            ...

    class can_be_pulled_defined(can_be_pulled.impl()):
        def __init__(self, signal: Electrical, ref: ElectricPower) -> None:
            super().__init__()
            self.ref = ref
            self.signal = signal

        def pull(self, up: bool):
            obj = self.get_obj()

            up_r, down_r = None, None
            if obj.has_trait(ElectricLogic.has_pulls):
                up_r, down_r = obj.get_trait(ElectricLogic.has_pulls).get_pulls()

            if up and up_r:
                return up_r
            if not up and down_r:
                return down_r

            resistor = Resistor()
            if up:
                obj.NODEs.pull_up = resistor
                up_r = resistor
            else:
                obj.NODEs.pull_down = resistor
                down_r = resistor

            self.signal.connect_via(
                resistor, self.ref.IFs.hv if up else self.ref.IFs.lv
            )

            obj.add_trait(ElectricLogic.has_pulls_defined(up_r, down_r))
            return resistor

    # class can_be_buffered(NodeTrait):
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
    #        obj = self.get_obj()
    #
    #        if hasattr(obj.NODEs, "buffer"):
    #            return cast_assert(SignalBuffer, getattr(obj.NODEs, "buffer"))
    #
    #        buffer = SignalBuffer()
    #        obj.NODEs.buffer = buffer
    #        self.signal.connect(buffer.NODEs.logic_in)
    #
    #        return buffer.NODEs.logic_out

    def __init__(self) -> None:
        super().__init__()

        class IFS(Logic.NODES()):
            reference = ElectricPower()
            signal = Electrical()

        self.IFs = IFS(self)

        class _can_be_surge_protected_defined(can_be_surge_protected_defined):
            def protect(_self):
                return [
                    tvs.builder(
                        lambda t: t.PARAMs.reverse_working_voltage.merge(
                            self.IFs.reference.PARAMs.voltage
                        )
                    )
                    for tvs in super().protect()
                ]

        self.add_trait(has_single_electric_reference_defined(self.IFs.reference))
        self.add_trait(
            _can_be_surge_protected_defined(self.IFs.reference.IFs.lv, self.IFs.signal)
        )
        self.add_trait(
            ElectricLogic.can_be_pulled_defined(
                self.IFs.signal,
                self.IFs.reference,
            )
        )

    def connect_to_electric(self, signal: Electrical, reference: ElectricPower):
        self.IFs.reference.connect(reference)
        self.IFs.signal.connect(signal)
        return self

    def connect_reference(self, reference: ElectricPower, invert: bool = False):
        if invert:
            # TODO
            raise NotImplementedError()
        #    inverted = ElectricPower()
        #    inverted.NODEs.lv.connect(reference.NODEs.hv)
        #    inverted.NODEs.hv.connect(reference.NODEs.lv)
        #    reference = inverted
        self.IFs.reference.connect(reference)

    def connect_references(self, other: "ElectricLogic", invert: bool = False):
        self.connect_reference(other.IFs.reference, invert=invert)

    def set(self, on: bool):
        r = self.IFs.reference.IFs
        self.IFs.signal.connect(r.hv if on else r.lv)

    @staticmethod
    def connect_all_references(ifs: Iterable["ElectricLogic"]) -> ElectricPower:
        out = connect_all_interfaces([x.IFs.reference for x in ifs])
        assert out
        return out

    @staticmethod
    def connect_all_node_references(
        nodes: Iterable[Node], gnd_only=False
    ) -> ElectricPower:
        # TODO check if any child contains ElectricLogic which is not connected
        # e.g find them in graph and check if any has parent without "single reference"

        refs = {
            x.get_trait(has_single_electric_reference).get_reference()
            for x in nodes
            if x.has_trait(has_single_electric_reference)
        } | {x for x in nodes if isinstance(x, ElectricPower)}
        assert refs

        if gnd_only:
            connect_all_interfaces({r.IFs.lv for r in refs})
            return next(iter(refs))

        connect_all_interfaces(refs)
        return next(iter(refs))

    @classmethod
    def connect_all_module_references(
        cls, node: Module | ModuleInterface, gnd_only=False
    ) -> ElectricPower:
        return cls.connect_all_node_references(
            node.IFs.get_all() + node.NODEs.get_all(),
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
        target = self.IFs.reference.IFs.hv if up else self.IFs.reference.IFs.lv
        if bridge_ref_to_signal:
            return target.connect_via(bridge, self.IFs.signal)
        return self.IFs.signal.connect_via(bridge, target)

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
            self.IFs.signal.connect(other.IFs.signal)
        if reference:
            self.IFs.reference.connect(other.IFs.reference)
        if lv:
            self.IFs.reference.IFs.lv.connect(other.IFs.reference.IFs.lv)

        return super().connect_shallow(other)
