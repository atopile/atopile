# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import inspect
import logging
from typing import Callable, Iterable

import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile import errors
from faebryk.libs.exceptions import accumulate

logger = logging.getLogger(__name__)


class ERCFault(errors.UserException):
    """Base class for ERC faults."""


class ERCFaultShort(ERCFault):
    """Exception raised for short circuits."""


class ERCFaultShortedInterfaces(ERCFaultShort):
    """Short circuit between two Interfaces."""

    def __init__(self, msg: str, path: fabll.Path, *args: object) -> None:
        super().__init__(msg, path, *args)
        self.path = path

    @classmethod
    def from_path(cls, path: fabll.Path) -> "ERCFaultShortedInterfaces":
        """
        Given two shorted Interfaces, return an exception that describes the
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


def simple_erc(G: graph.GraphView):
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
        electricpower = fabll.Node.bind_typegraph(G).nodes_of_type(F.ElectricPower)
        logger.info(f"Checking {len(electricpower)} Power")

        buses_grouped = fabll.is_interface.group_into_buses(electricpower)
        buses = list(buses_grouped.values())

        # We do collection both inside and outside the loop because we don't
        # want to continue the loop if we've already raised a short exception
        with accumulator.collect():
            logger.info("Checking for hv/lv shorts")
            for ep in electricpower:
                if mif_path := fabll.Path.from_connection(ep.lv, ep.hv):

                    def _keep_head(x: fabll.Node) -> bool:
                        if parent := x.get_parent():
                            parent_node, _ = parent
                            if isinstance(parent_node, F.ElectricPower):
                                return parent_node.hv is not x

                        return True

                    def _keep_tail(x: fabll.Node) -> bool:
                        if parent := x.get_parent():
                            parent_node, _ = parent
                            if isinstance(parent_node, F.ElectricPower):
                                return parent_node.lv is not x

                        return True

                    raise ERCFaultShortedInterfaces.from_path(
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
        nets = fabll.Node.bind_typegraph(G).nodes_of_type(F.Net)
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

        comps = fabll.Node.bind_typegraph(G).nodes_of_types(
            (F.Resistor, F.Capacitor, F.Fuse)
        )
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

                if path := fabll.Path.from_connection(comp.unnamed[0], comp.unnamed[1]):
                    raise ERCFaultShortedInterfaces.from_path(path)

        ## unmapped Electricals
        # fps = [n for n in nodes if isinstance(n, Footprint)]
        # logger.info(f"Checking {len(fps)} footprints")
        # for fp in fps:
        #    for mif in fp.get_all():
        #        if not mif.get_direct_connections():
        #            raise ERCFault([mif], "no connections")

        # TODO check multiple pulls per logic


def check_modules_for_erc(module: Iterable[fabll.Module]):
    for m in module:
        logger.info(f"Checking {m} {'-' * 20}")
        simple_erc(m.get_graph())


def check_classes_for_erc(classes: Iterable[Callable[[], fabll.Module]]):
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
    module_classes = [m[1] for m in members if issubclass(m[1], fabll.Module)]
    check_classes_for_erc(module_classes)


# TODO split this up
class needs_erc_check(fabll.Node):
    _is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()

    design_check = F.implements_design_check.MakeChild()

    # TODO: Implement this
    @F.implements_design_check.register_post_design_check
    def __check_post_design__(self):
        simple_erc(self.get_graph())
