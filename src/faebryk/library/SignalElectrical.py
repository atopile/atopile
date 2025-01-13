# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Iterable

import faebryk.library._F as F
from faebryk.core.link import LinkDirectConditional, LinkDirectConditionalFilterResult
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import CNode, Node
from faebryk.libs.library import L


class SignalElectrical(F.Signal):
    class LinkIsolatedReference(LinkDirectConditional):
        def test(self, node: CNode):
            return not isinstance(node, F.ElectricPower)

        def __init__(self) -> None:
            super().__init__(
                lambda path: LinkDirectConditionalFilterResult.FILTER_PASS
                if all(self.test(dst.node) for dst in path)
                else LinkDirectConditionalFilterResult.FILTER_FAIL_UNRECOVERABLE,
                needs_only_first_in_path=False,
            )

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    # line is a better name, but for compatibility with Logic we use signal
    # might change in future
    signal: F.Electrical
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
    def connect_all_references(ifs: Iterable["SignalElectrical"]) -> F.ElectricPower:
        return F.ElectricPower.connect(*[x.reference for x in ifs])

    @L.rt_field
    def surge_protected(self):
        class _can_be_surge_protected_defined(F.can_be_surge_protected_defined):
            def protect(_self, owner: Module):
                out = super().protect(owner)
                for tvs in out.get_children(direct_only=False, types=F.TVS):
                    tvs.reverse_working_voltage.alias_is(self.reference.voltage)
                return out

        return _can_be_surge_protected_defined(self.reference.lv, self.signal)
