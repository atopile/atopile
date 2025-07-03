# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import inspect
import logging
from typing import Callable, Iterable, cast

from more_itertools import first

import faebryk.library._F as F
from atopile import errors
from faebryk.core.cpp import Path
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.trait import Trait
from faebryk.libs.exceptions import accumulate
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class ERCFault(errors.UserException):
    """Base class for ERC faults."""


class ModuleInterfacePath(list[ModuleInterface]):
    """A path of ModuleInterfaces."""

    @classmethod
    def from_path(cls, path: Path) -> "ModuleInterfacePath":
        """
        Convert a Path (of GraphInterfaces) to a ModuleInterfacePath.
        """
        mifs = cast(
            list[ModuleInterface],
            [gif.node for gif in path if gif.node.isinstance(ModuleInterface)],
        )
        return cls(mifs)

    def snip_head(
        self, scissors: Callable[[ModuleInterface], bool], include_last: bool = True
    ) -> "ModuleInterfacePath":
        """
        Keep the head until the scissors predicate returns False.
        """
        for i, mif in enumerate(self):
            if not scissors(mif):
                return type(self)(self[: i + include_last])
        return self

    def snip_tail(
        self, scissors: Callable[[ModuleInterface], bool], include_first: bool = True
    ) -> "ModuleInterfacePath":
        """
        Keep the tail until the scissors predicate returns False.
        """
        for i, mif in reversed(list(enumerate(self))):
            if not scissors(mif):
                return type(self)(self[i + (not include_first) :])
        return self

    @classmethod
    def from_connection(
        cls, a: ModuleInterface, b: ModuleInterface
    ) -> "ModuleInterfacePath | None":
        """
        Return a ModuleInterfacePath between two ModuleInterfaces, if it exists,
        else None.
        """
        if paths := a.is_connected_to(b):
            # FIXME: Notes: from the master of graphs:
            #  - iterate through all paths
            #  - make a helper function
            #    ModuleInterfacePath.get_subpaths(path: Path, search: SubpathSearch)
            #    e.g SubpathSearch = tuple[Callable[[ModuleInterface], bool], ...]
            #  - choose out of subpaths
            #    - be careful with LinkDirectDerived edges (if there is a faulting edge
            #      is derived, save it as candidate and only yield it if no other found)
            #    - choose first shortest
            return cls.from_path(first(paths))
        return None


class ERCFaultShort(ERCFault):
    """Exception raised for short circuits."""


class ERCFaultShortedModuleInterfaces(ERCFaultShort):
    """Short circuit between two ModuleInterfaces."""

    def __init__(self, msg: str, path: ModuleInterfacePath, *args: object) -> None:
        super().__init__(msg, path, *args)
        self.path = path

    @classmethod
    def from_path(cls, path: ModuleInterfacePath) -> "ERCFaultShortedModuleInterfaces":
        """
        Given two shorted ModuleInterfaces, return an exception that describes the
        narrowest path for the fault.
        """
        return cls(f"`{' ~ '.join(mif.get_full_name() for mif in path)}`", path)


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

        buses_grouped = ModuleInterface._group_into_buses(electricpower)
        buses = list(buses_grouped.values())

        # We do collection both inside and outside the loop because we don't
        # want to continue the loop if we've already raised a short exception
        with accumulator.collect():
            logger.info("Checking for hv/lv shorts")
            for ep in electricpower:
                if mif_path := ModuleInterfacePath.from_connection(ep.lv, ep.hv):

                    def _keep_head(x: ModuleInterface) -> bool:
                        if parent := x.get_parent():
                            parent_node, _ = parent
                            if isinstance(parent_node, F.ElectricPower):
                                return parent_node.hv is not x

                        return True

                    def _keep_tail(x: ModuleInterface) -> bool:
                        if parent := x.get_parent():
                            parent_node, _ = parent
                            if isinstance(parent_node, F.ElectricPower):
                                return parent_node.lv is not x

                        return True

                    raise ERCFaultShortedModuleInterfaces.from_path(
                        mif_path.snip_head(_keep_head).snip_tail(_keep_tail)
                    )

            logger.info("Checking for power source shorts")
            for bus in buses:
                with accumulator.collect():
                    sources = {
                        ep for ep in bus if ep.has_trait(F.Power.is_power_source)
                    }
                    if len(sources) <= 1:
                        continue

                    friendly_sources = ", ".join(n.get_full_name() for n in sources)
                    raise ERCPowerSourcesShortedError(
                        f"Power sources shorted: {friendly_sources}"
                    )

        # shorted nets
        nets = GraphFunctions(G).nodes_of_type(F.Net)
        logger.info(f"Checking {len(nets)} explicit nets")
        for net in nets:
            with accumulator.collect():
                nets_on_bus = F.Net.find_nets_for_mif(net.part_of)

                named_collisions = {
                    neighbor_net
                    for neighbor_net in nets_on_bus
                    if neighbor_net.has_trait(F.has_overriden_name)
                }

                if named_collisions:
                    friendly_shorted = ", ".join(
                        n.get_full_name() for n in named_collisions
                    )
                    raise ERCFaultShort(
                        f"Shorted nets: {friendly_shorted}",
                    )

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

                if path := ModuleInterfacePath.from_connection(
                    comp.unnamed[0], comp.unnamed[1]
                ):
                    raise ERCFaultShortedModuleInterfaces.from_path(path)

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
        logger.info(f"Checking {m} {'-' * 20}")
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


# TODO split this up
class needs_erc_check(Trait.decless()):
    design_check: F.implements_design_check

    @F.implements_design_check.register_post_design_check
    def __check_post_design__(self):
        simple_erc(self.get_graph())
