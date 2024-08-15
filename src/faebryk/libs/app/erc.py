# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import inspect
import logging
from typing import Callable, Iterable, Sequence

from faebryk.core.core import Graph, Module, ModuleInterface
from faebryk.core.util import (
    get_all_nodes_of_type,
    get_all_nodes_of_types,
)
from faebryk.library.has_overriden_name import has_overriden_name
from faebryk.libs.picker.picker import has_part_picked
from faebryk.libs.util import groupby, print_stack

logger = logging.getLogger(__name__)


class ERCFault(Exception):
    def __init__(self, faulting_ifs: Sequence[ModuleInterface], *args: object) -> None:
        super().__init__(*args, faulting_ifs)
        self.faulting_ifs = faulting_ifs


class ERCFaultShort(ERCFault):
    def __init__(self, faulting_ifs: Sequence[ModuleInterface], *args: object) -> None:
        link = faulting_ifs[0].is_connected_to(faulting_ifs[1])
        assert link
        from faebryk.core.core import LINK_TB

        stack = ""
        if LINK_TB:
            stack = print_stack(link.tb)

        super().__init__(faulting_ifs, *args)
        print(stack)


def simple_erc(G: Graph):
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
    from faebryk.library.Capacitor import Capacitor
    from faebryk.library.ElectricPower import ElectricPower
    from faebryk.library.Fuse import Fuse
    from faebryk.library.Net import Net
    from faebryk.library.Resistor import Resistor

    logger.info("Checking graph for ERC violations")

    # power short
    electricpower = get_all_nodes_of_type(G, ElectricPower)
    logger.info(f"Checking {len(electricpower)} Power")
    for ep in electricpower:
        if ep.IFs.lv.is_connected_to(ep.IFs.hv):
            raise ERCFaultShort([ep], "shorted power")

    # shorted nets
    nets = get_all_nodes_of_type(G, Net)
    logger.info(f"Checking {len(nets)} nets")
    for net in nets:
        collisions = {
            p[0]
            for mif in net.IFs.part_of.get_direct_connections()
            if (p := mif.get_parent()) and isinstance(p[0], Net)
        }

        if collisions:
            shorted = collisions | {net}
            raise ERCFaultShort(
                [n.IFs.part_of for n in shorted], f"shorted nets: {shorted}"
            )

    # net name collisions
    net_name_collisions = {
        k: v
        for k, v in groupby(
            nets, lambda n: n.get_trait(has_overriden_name).get_name()
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
    #    mifs = set(fp.IFs.get_all())
    #    checked = set()
    #    for mif in mifs:
    #        checked.add(mif)
    #        if any(mif.is_connected_to(other) for other in (mifs - checked)):
    #            raise ERCFault([mif], "shorted symmetric footprint")
    comps = get_all_nodes_of_types(G, (Resistor, Capacitor, Fuse))
    for comp in comps:
        assert isinstance(comp, (Resistor, Capacitor, Fuse))
        # TODO make prettier
        if (
            comp.has_trait(has_part_picked)
            and comp.get_trait(has_part_picked).get_part().partno == "REMOVE"
        ):
            continue
        if comp.IFs.unnamed[0].is_connected_to(comp.IFs.unnamed[1]):
            raise ERCFaultShort(comp.IFs.unnamed, "shorted component")

    ## unmapped Electricals
    # fps = [n for n in nodes if isinstance(n, Footprint)]
    # logger.info(f"Checking {len(fps)} footprints")
    # for fp in fps:
    #    for mif in fp.IFs.get_all():
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
