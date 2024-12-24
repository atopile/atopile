# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import inspect
import logging
from typing import Callable, Iterable, Sequence

import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.units import P
from faebryk.libs.util import groupby

logger = logging.getLogger(__name__)


class ERCFault(Exception):
    def __init__(self, faulting_ifs: Sequence[ModuleInterface], *args: object) -> None:
        super().__init__(*args, faulting_ifs)
        self.faulting_ifs = faulting_ifs


class ERCFaultShort(ERCFault):
    def __init__(self, faulting_ifs: Sequence[ModuleInterface], *args: object) -> None:
        paths = faulting_ifs[0].is_connected_to(faulting_ifs[1])
        assert paths

        super().__init__(faulting_ifs, *args)


class ERCFaultElectricPowerUndefinedVoltage(ERCFault):
    def __init__(self, faulting_EP: F.ElectricPower, *args: object) -> None:
        msg = (
            f"ElectricPower with undefined or unsolved voltage: {faulting_EP}:"
            f" {faulting_EP.voltage}"
        )
        super().__init__([faulting_EP], msg, *args)


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

    # shorted power
    electricpower = GraphFunctions(G).nodes_of_type(F.ElectricPower)
    logger.info(f"Checking {len(electricpower)} Power")
    for ep in electricpower:
        if ep.lv.is_connected_to(ep.hv):
            raise ERCFaultShort([ep], "shorted power")
        if ep.has_trait(F.Power.is_power_source):
            other_sources = [
                other
                for other in ep.get_connected()
                if isinstance(other, F.ElectricPower)
                and other.has_trait(F.Power.is_power_source)
            ]
            if other_sources:
                raise ERCPowerSourcesShortedError([ep] + other_sources)

    # shorted nets
    nets = GraphFunctions(G).nodes_of_type(F.Net)
    logger.info(f"Checking {len(nets)} explicit nets")
    for net in nets:
        collisions = {
            p[0]
            for mif in net.part_of.get_connected()
            if (p := mif.get_parent()) and isinstance(p[0], F.Net)
        }

        if collisions:
            shorted = collisions | {net}
            raise ERCFaultShort(
                [n.part_of for n in shorted], f"shorted nets: {shorted}"
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
        raise ERCFault([], f"Net name collision: {net_name_collisions}")

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
        assert isinstance(comp, (F.Resistor, F.Capacitor, F.Fuse))
        # TODO make prettier
        if (
            comp.has_trait(F.has_part_picked)
            and comp.get_trait(F.has_part_picked).removed
        ):
            continue
        if comp.unnamed[0].is_connected_to(comp.unnamed[1]):
            raise ERCFaultShort(comp.unnamed, "shorted component")

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
