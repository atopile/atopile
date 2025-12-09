# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import pytest

import faebryk.core.faebrykpy as fbrk
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
        return cls(f"`{path!r}`", path)


class ERCFaultElectricPowerUndefinedVoltage(ERCFault):
    def __init__(self, faulting_EP: "F.ElectricPower", *args: object) -> None:
        msg = (
            f"ElectricPower with undefined or unsolved voltage: {faulting_EP}:"
            f" {faulting_EP.voltage}"
        )
        super().__init__(msg, [faulting_EP], *args)


class ERCPowerSourcesShortedError(ERCFault):
    """
    Multiple power sources shorted together
    """


def simple_erc(tg: fbrk.TypeGraph):
    """Simple ERC check.

    This function will check for the following ERC violations:
    - shorted ElectricPower
    - shorted Caps
    - shorted Resistors
    - shorted symmetric footprints
    - shorted Nets
    - Net name collision

    - [unmapped pins for footprints]
    """
    logger.info("Checking graph for ERC violations")

    with accumulate(ERCFault) as accumulator:
        # shorted power
        electricpower = F.ElectricPower.bind_typegraph(tg).get_instances(
            g=tg.get_graph_view()
        )
        logger.info(f"Checking {len(electricpower)} Power")

        buses_grouped = fabll.is_interface.group_into_buses(set(electricpower))
        buses = list(buses_grouped.values())

        # We do collection both inside and outside the loop because we don't
        # want to continue the loop if we've already raised a short exception
        with accumulator.collect():
            logger.info("Checking for hv/lv shorts")
            for ep in electricpower:
                if path := fabll.Path.from_connection(ep.lv.get(), ep.hv.get()):
                    raise ERCFaultShortedInterfaces.from_path(path)

            logger.info("Checking for power source shorts")
            for bus in buses:
                with accumulator.collect():
                    sources = {ep for ep in bus if ep.has_trait(F.is_source)}
                    if len(sources) <= 1:
                        continue

                    friendly_sources = ", ".join(n.get_full_name() for n in sources)
                    raise ERCPowerSourcesShortedError(
                        f"Power sources shorted: {friendly_sources}"
                    )

        # shorted nets
        nets = F.Net.bind_typegraph(tg).get_instances(g=tg.get_graph_view())
        logger.info(f"Checking {len(nets)} explicit nets")
        for net in nets:
            with accumulator.collect():
                nets_on_bus = F.Net.find_nets_for_mif(net.part_of.get())

                named_collisions = {
                    neighbor_net
                    for neighbor_net in nets_on_bus
                    if neighbor_net.has_trait(F.has_net_name)
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
        #    if n.has_trait(F.Footprints.can_attach_to_footprint)
        # ]
        # logger.info(f"Checking {len(sym_fps)} symmetric footprints")
        # for fp in sym_fps:
        #    mifs = set(fp.get_all())
        #    checked = set()
        #    for mif in mifs:
        #        checked.add(mif)
        #        if any(mif.is_connected_to(other) for other in (mifs - checked)):
        #            raise ERCFault([mif], "shorted symmetric footprint")

        comps = fabll.Node.bind_typegraph(tg).nodes_of_types(
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

                if path := fabll.Path.from_connection(
                    comp.unnamed[0].get(), comp.unnamed[1].get()
                ):
                    raise ERCFaultShortedInterfaces.from_path(path)

        ## unmapped Electricals
        # fps = [n for n in nodes if isinstance(n, Footprint)]
        # logger.info(f"Checking {len(fps)} footprints")
        # for fp in fps:
        #    for mif in fp.get_all():
        #        if not mif.get_direct_connections():
        #            raise ERCFault([mif], "no connections")

        # TODO check multiple pulls per logic


# TODO split this up
class needs_erc_check(fabll.Node):
    is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()

    design_check = F.implements_design_check.MakeChild()

    # TODO: Implement this
    @F.implements_design_check.register_post_design_check
    def __check_post_design__(self):
        simple_erc(self.tg)


class Test:
    def test_erc_isolated_connect(self):
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        electricPowerType = F.ElectricPower.bind_typegraph(tg)

        y1 = electricPowerType.create_instance(g=g)
        y2 = electricPowerType.create_instance(g=g)

        y1.make_source()
        y2.make_source()

        with pytest.raises(ERCPowerSourcesShortedError):
            y1._is_interface.get().connect_to(y2)
            simple_erc(tg)

        # TODO no more LDO in fabll
        # ldo1 = F.LDO()
        # ldo2 = F.LDO()

        # with pytest.raises(ERCPowerSourcesShortedError):
        #     ldo1.power_out.connect(ldo2.power_out)
        #     simple_erc(ldo1.get_graph())

        i2cType = F.I2C.bind_typegraph(tg)
        a1 = i2cType.create_instance(g=g)
        b1 = i2cType.create_instance(g=g)

        a1._is_interface.get().connect_to(b1)
        assert a1._is_interface.get().is_connected_to(b1)
        assert a1.scl.get()._is_interface.get().is_connected_to(b1.scl.get())
        assert a1.sda.get()._is_interface.get().is_connected_to(b1.sda.get())

        assert not a1.scl.get()._is_interface.get().is_connected_to(b1.sda.get())
        assert not a1.sda.get()._is_interface.get().is_connected_to(b1.scl.get())

    def test_erc_electric_power_short(self):
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        electricPowerType = F.ElectricPower.bind_typegraph(tg)
        ep1 = electricPowerType.create_instance(g=g)
        ep2 = electricPowerType.create_instance(g=g)

        ep1._is_interface.get().connect_to(ep2)

        # This is okay!
        simple_erc(tg)

        ep1.lv.get()._is_interface.get().connect_to(ep2.hv.get())

        # This is not okay!
        with pytest.raises(ERCFaultShortedInterfaces) as ex:
            simple_erc(tg)

        # TODO figure out a nice way to format paths for this
        print(ex.value.path)
        # assert set(ex.value.path) == {ep1.lv, ep2.hv}

    def test_erc_power_source_short(self):
        """
        Test that a power source is shorted when connected to another power source
        """
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        power_out_1 = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)
        power_out_2 = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)

        power_out_1._is_interface.get().connect_to(power_out_2)
        power_out_2._is_interface.get().connect_to(power_out_1)

        power_out_1.make_source()
        power_out_2.make_source()

        with pytest.raises(ERCPowerSourcesShortedError):
            simple_erc(tg)

    def test_erc_power_source_no_short(self):
        """
        Test that a power source is not shorted when connected to another
        non-power source
        """
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        power_out_1 = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)
        power_out_2 = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)

        power_out_1.make_source()

        power_out_1._is_interface.get().connect_to(power_out_2)

        simple_erc(tg)
