# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import inspect
import logging
from typing import Callable, Iterable, Sequence

import faebryk.library._F as F
from faebryk.core.graphinterface import Graph
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.library.Operation import Operation
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


class ERCFaultElectricPowerUndefinedVoltage(ERCFault):
    def __init__(self, faulting_EP: list[F.ElectricPower], *args: object) -> None:
        faulting_EP = list(sorted(faulting_EP, key=lambda ep: ep.get_name()))
        msg = "ElectricPower(s) with undefined or unsolved voltage: " + ",\n ".join(
            f"{ep}: {ep.voltage}" for ep in faulting_EP
        )
        super().__init__(faulting_EP, msg, *args)


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
    logger.info("Checking graph for ERC violations")

    # power short and power with undefined voltage
    electricpower = G.nodes_of_type(F.ElectricPower)
    logger.info(f"Checking {len(electricpower)} Power")
    for ep in electricpower:
        if ep.lv.is_connected_to(ep.hv):
            raise ERCFaultShort([ep], "shorted power")

    unresolved_voltage = [
        ep
        for ep in electricpower
        if isinstance(ep.voltage.get_most_narrow(), (F.TBD, Operation))
    ]

    if unresolved_voltage:
        raise ERCFaultElectricPowerUndefinedVoltage(unresolved_voltage)

    # shorted nets
    nets = G.nodes_of_type(F.Net)
    logger.info(f"Checking {len(nets)} nets")
    for net in nets:
        collisions = {
            p[0]
            for mif in net.part_of.get_direct_connections()
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
    comps = G.nodes_of_types((F.Resistor, F.Capacitor, F.Fuse))
    for comp in comps:
        assert isinstance(comp, (F.Resistor, F.Capacitor, F.Fuse))
        # TODO make prettier
        if (
            comp.has_trait(has_part_picked)
            and comp.get_trait(has_part_picked).get_part().partno == "REMOVE"
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
