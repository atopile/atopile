# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import inspect
import logging
from typing import Callable, Iterable

from more_itertools import first

import faebryk.library._F as F
from atopile import errors
from faebryk.core.cpp import GraphInterface
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.exceptions import accumulate
from faebryk.libs.units import P
from faebryk.libs.util import groupby

logger = logging.getLogger(__name__)


class ERCFault(errors.UserException):
    """Base class for ERC faults."""


class ERCFaultShort(ERCFault):
    """Short circuit between two ModuleInterfaces."""

    @staticmethod
    def narrow_from_pair(
        a: ModuleInterface,
        b: ModuleInterface,
        is_a: Callable[[GraphInterface], bool],
        is_b: Callable[[GraphInterface], bool],
    ) -> list[GraphInterface]:
        """
        Given two shorted ModuleInterfaces, return the narrowest path for the fault.
        """
        gifs_on_path = list(first(a.is_connected_to(b)))  # type: ignore

        # max to min index sweep of "is_a" to find the highest index
        # gif which passes the predicate
        for max_a_i, gif in reversed(list(enumerate(gifs_on_path))):
            if is_a(gif):
                break
        else:
            raise ValueError("No node passing is_a found on path")

        # min to max index sweep of "is_b" to find the lowest index
        # gif which passes the predicate
        for min_b_i, gif in enumerate(gifs_on_path):
            if is_b(gif):
                break
        else:
            raise ValueError("No node passing is_b found on path")

        return gifs_on_path[max_a_i : min_b_i + 1]

    @classmethod
    def from_pair(
        cls,
        a: ModuleInterface,
        b: ModuleInterface,
        is_a: Callable[[GraphInterface], bool],
        is_b: Callable[[GraphInterface], bool],
    ) -> "ERCFaultShort":
        """
        Given two shorted ModuleInterfaces, return an exception that describes the
        narrowest path for the fault.
        """
        shortest_path = cls.narrow_from_pair(a, b, is_a, is_b)
        friendly_shortest_path = " ~ ".join(
            gif.node.get_full_name() for gif in shortest_path
        )
        return cls(f"`{a}` and `{b}` are shorted by `{friendly_shortest_path}`")


class ERCFaultElectricPowerUndefinedVoltage(ERCFault):
    def __init__(self, faulting_EP: F.ElectricPower, *args: object) -> None:
        msg = (
            f"ElectricPower with undefined or unsolved voltage: {faulting_EP}:"
            f" {faulting_EP.voltage}"
        )
        super().__init__(msg, [faulting_EP], *args)


class ERCPowerSourcesShortedError(ERCFault):
    """
    Multiple power sources shorted together
    """


def simple_erc(G: Graph, voltage_limit=1e5 * P.V):
    """Simple ERC check.

    This function will check for the following ERC violations:
    - shorted ElectricPower
    - shorted Caps
    - shorted Resistors
    - shorted symmetric footprints
    - shorted Nets
    - Net name collision

    - [unmapped pins for footprints]

    Args:

    Returns:
    """
    logger.info("Checking graph for ERC violations")

    with accumulate(ERCFault) as accumulator:
        # shorted power
        electricpower = GraphFunctions(G).nodes_of_type(F.ElectricPower)
        logger.info(f"Checking {len(electricpower)} Power")

        # We do collection both inside and outside the loop because we don't
        # want to continue the loop if we've already raised a short exception
        with accumulator.collect():
            for ep in electricpower:
                if ep.lv.is_connected_to(ep.hv):

                    def _is_lv(x: GraphInterface) -> bool:
                        if parent := x.node.get_parent():
                            _, parent_name = parent
                            return parent_name == "lv"

                        return False

                    def _is_hv(x: GraphInterface) -> bool:
                        if parent := x.node.get_parent():
                            _, parent_name = parent
                            return parent_name == "hv"

                        return False

                    raise ERCFaultShort.from_pair(ep.lv, ep.hv, _is_lv, _is_hv)

                with accumulator.collect():
                    if ep.has_trait(F.Power.is_power_source):
                        other_sources = [
                            other
                            for other in ep.get_connected()
                            if isinstance(other, F.ElectricPower)
                            and other.has_trait(F.Power.is_power_source)
                        ]
                        if other_sources:
                            friendly_sources = ", ".join(
                                n.get_full_name() for n in [ep] + other_sources
                            )
                            raise ERCPowerSourcesShortedError(
                                f"Power sources shorted: {friendly_sources}"
                            )

        # shorted nets
        nets = GraphFunctions(G).nodes_of_type(F.Net)
        logger.info(f"Checking {len(nets)} explicit nets")
        for net in nets:
            with accumulator.collect():
                collisions = {
                    p[0]
                    for mif in net.part_of.get_connected()
                    if (p := mif.get_parent()) and isinstance(p[0], F.Net)
                }

                if collisions:
                    friendly_shorted = ", ".join(n.get_full_name() for n in collisions)
                    raise ERCFaultShort(
                        f"Shorted nets: {friendly_shorted}",
                    )

        # net name collisions
        net_name_collisions = {
            k: v
            for k, v in groupby(
                nets, lambda n: n.get_trait(F.has_overriden_name).get_name()
            ).items()
            if len(v) > 1
        }
        if net_name_collisions:
            raise ERCFault(f"Net name collision: {net_name_collisions}")

        # shorted components
        # parts = [n for n in nodes if n.has_trait(has_footprint)]
        # sym_fps = [
        #    n.get_trait(has_footprint).get_footprint()
        #    for n in parts
        #    if n.has_trait(can_attach_to_footprint_symmetrically)
        # ]
        # logger.info(f"Checking {len(sym_fps)} symmetric footprints")
        # for fp in sym_fps:
        #    mifs = set(fp.get_all())
        #    checked = set()
        #    for mif in mifs:
        #        checked.add(mif)
        #        if any(mif.is_connected_to(other) for other in (mifs - checked)):
        #            raise ERCFault([mif], "shorted symmetric footprint")

        comps = GraphFunctions(G).nodes_of_types((F.Resistor, F.Capacitor, F.Fuse))
        logger.info(f"Checking {len(comps)} passives")
        for comp in comps:
            with accumulator.collect():
                assert isinstance(comp, (F.Resistor, F.Capacitor, F.Fuse))
                # TODO make prettier
                if (
                    comp.has_trait(F.has_part_picked)
                    and comp.get_trait(F.has_part_picked).removed
                ):
                    continue

                if comp.unnamed[0].is_connected_to(comp.unnamed[1]):
                    raise ERCFaultShort(
                        f"Shorted component: {comp.get_full_name()}",
                    )

        ## unmapped Electricals
        # fps = [n for n in nodes if isinstance(n, Footprint)]
        # logger.info(f"Checking {len(fps)} footprints")
        # for fp in fps:
        #    for mif in fp.get_all():
        #        if not mif.get_direct_connections():
        #            raise ERCFault([mif], "no connections")

        # TODO check multiple pulls per logic


def check_modules_for_erc(module: Iterable[Module]):
    for m in module:
        logger.info(f"Checking {m} {'-'*20}")
        simple_erc(m.get_graph())


def check_classes_for_erc(classes: Iterable[Callable[[], Module]]):
    modules = []
    for c in classes:
        try:
            m = c()
        except Exception as e:
            logger.warning(
                f"Could not instantiate {c.__name__}: {type(e).__name__}({e})"
            )
            continue
        modules.append(m)
    check_modules_for_erc(modules)


def check_library_for_erc(lib):
    members = inspect.getmembers(lib, inspect.isclass)
    module_classes = [m[1] for m in members if issubclass(m[1], Module)]
    check_classes_for_erc(module_classes)
