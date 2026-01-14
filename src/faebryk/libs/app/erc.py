# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from atopile import errors
from faebryk.libs.app.checks import check_design
from faebryk.libs.exceptions import accumulate

logger = logging.getLogger(__name__)


class ERCFault(errors.UserException):
    """Base class for ERC faults."""


class ERCFaultShort(ERCFault):
    """Exception raised for short circuits."""


class ERCFaultShortedInterfaces(ERCFaultShort):
    """Short circuit between two Interfaces."""

    def __init__(self, msg: str, path: fabll.Path, *args: object) -> None:
        super().__init__(msg, path, *args, markdown=False)
        self.path = path

    @classmethod
    def from_path(cls, path: fabll.Path) -> "ERCFaultShortedInterfaces":
        """
        Given two shorted Interfaces, return an exception that describes the
        narrowest path for the fault.
        """

        start = path.get_start_node().pretty_repr()
        end = path.get_end_node().pretty_repr()
        return cls(
            f"Shorted:\t{start} -> {end}\nFull path:\t{path.pretty_repr()}", path
        )


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


# TODO split this up
class needs_erc_check(fabll.Node):
    """
    Implement checks:
    - shorted interfaces:
        - ElectricPower (hv and lv)
    - shorted components:
        - Capacitor (unnamed[0] and unnamed[1])
        - Resistor (unnamed[0] and unnamed[1])
        - Fuse (unnamed[0] and unnamed[1])
    - shorted nets
    - net name collisions

    TODO
    - shorted ElectricPower sources
    - shorted symmetric footprints
    - [unmapped pins for footprints]
    """
    is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()
    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    # TODO: Implement this
    @F.implements_design_check.register_post_design_check
    def __check_post_design__(self):
        logger.info("Checking for ERC violations")
        with accumulate(ERCFault) as accumulator:
            self._check_shorted_interfaces_and_components()
            self._check_shorted_nets(accumulator)
            self._check_shorted_electric_power_sources(accumulator)
            self._check_additional_heuristics()

    def _check_shorted_interfaces_and_components(self) -> None:
        comps = fabll.Node.bind_typegraph(self.tg).nodes_of_types(
            (F.Resistor, F.Capacitor, F.Fuse, F.ElectricPower)
        )
        logger.info(f"Checking {len(comps)} elements for shorts")

        electrical_instances = {
            elec
            for comp in comps
            for elec in comp.get_children(direct_only=True, types=F.Electrical)
        }

        electrical_buses = fabll.is_interface.group_into_buses(electrical_instances)

        logger.info(
            "Grouped %s electricals into %s buses",
            len(electrical_instances),
            len(electrical_buses),
        )

        for comp in comps:
            if isinstance(comp, F.ElectricPower):
                e1 = comp.hv.get()
                e2 = comp.lv.get()
            else:
                e1 = comp.unnamed[0].get()
                e2 = comp.unnamed[1].get()
            if any(e1 in bus and e2 in bus for bus in electrical_buses.values()):
                path = fabll.Path.from_connection(e1, e2)
                assert path is not None
                raise ERCFaultShortedInterfaces.from_path(path)

    def _check_shorted_nets(self, accumulator: accumulate) -> None:
        nets = F.Net.bind_typegraph(self.tg).get_instances(
            g=self.tg.get_graph_view()
        )
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
                    raise ERCFaultShort(f"Shorted nets: {friendly_shorted}")

    def _check_shorted_electric_power_sources(
        self, accumulator: accumulate
    ) -> None:
        # shorted power
        electricpower = F.ElectricPower.bind_typegraph(self.tg).get_instances(
            g=self.tg.get_graph_view()
        )
        ep_buses = fabll.is_interface.group_into_buses(electricpower)

        # We do collection both inside and outside the loop because we don't
        # want to continue the loop if we've already raised a short exception
        with accumulator.collect():
            logger.info("Checking for power source shorts")
            for ep_bus in ep_buses.values():
                with accumulator.collect():
                    sources = {ep for ep in ep_bus if ep.has_trait(F.is_source)}
                    if len(sources) <= 1:
                        continue

                    friendly_sources = ", ".join(n.get_full_name() for n in sources)
                    raise ERCPowerSourcesShortedError(
                        f"Power sources shorted: {friendly_sources}"
                    )

    def _check_additional_heuristics(self) -> None:
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

        ## unmapped Electricals
        # fps = [n for n in nodes if isinstance(n, Footprint)]
        # logger.info(f"Checking {len(fps)} footprints")
        # for fp in fps:
        #    for mif in fp.get_all():
        #        if not mif.get_direct_connections():
        #            raise ERCFault([mif], "no connections")

        # TODO check multiple pulls per logic
        pass




class Test:
    class _App(fabll.Node):
        is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    def _run_post_design_checks(self, tg: fbrk.TypeGraph) -> None:
        g = tg.get_graph_view()
        app_type = self._App.bind_typegraph(tg)
        app = app_type.create_instance(g=g)
        fabll.Traits.create_and_add_instance_to(app, needs_erc_check)
        check_design(app, F.implements_design_check.CheckStage.POST_DESIGN)

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
            self._run_post_design_checks(tg)

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
        self._run_post_design_checks(tg)

        ep1.lv.get()._is_interface.get().connect_to(ep2.hv.get())

        # This is not okay!
        with pytest.raises(ERCFaultShortedInterfaces) as ex:
            self._run_post_design_checks(tg)

        # TODO figure out a nice way to format paths for this
        print(ex.value.path)
        # assert set(ex.value.path) == {ep1.lv, ep2.hv}

    def test_erc_electric_power_short_multiple_paths(self):
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        electricPowerType = F.ElectricPower.bind_typegraph(tg)
        eps = [electricPowerType.create_instance(g=g) for _ in range(4)]

        for i in range(3):
            eps[i]._is_interface.get().connect_to(eps[i + 1])

        eps[0].hv.get()._is_interface.get().connect_to(eps[3].lv.get())

        with pytest.raises(ERCFaultShortedInterfaces):
            self._run_post_design_checks(tg)

    def test_erc_electric_power_short_via_resistor_no_short(self):
        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        electricPowerType = F.ElectricPower.bind_typegraph(tg)
        ep1 = electricPowerType.create_instance(g=g)
        resistor = F.Resistor.bind_typegraph(tg).create_instance(g=g)

        ep1.hv.get()._is_interface.get().connect_to(resistor.unnamed[0].get())
        ep1.lv.get()._is_interface.get().connect_to(resistor.unnamed[1].get())

        # should not raise
        self._run_post_design_checks(tg)

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
            self._run_post_design_checks(tg)

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

        self._run_post_design_checks(tg)
