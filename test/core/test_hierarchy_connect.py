# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import unittest
from itertools import chain

import faebryk.library._F as F
from faebryk.core.core import logger as core_logger
from faebryk.core.link import LinkDirect, LinkDirectShallow, _TLinkDirectShallow
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L
from faebryk.libs.util import print_stack, times

logger = logging.getLogger(__name__)
core_logger.setLevel(logger.getEffectiveLevel())


class TestHierarchy(unittest.TestCase):
    def test_up_connect(self):
        class UARTBuffer(Module):
            bus_in: F.UART_Base
            bus_out: F.UART_Base

            def __preinit__(self) -> None:
                bus_in = self.bus_in
                bus_out = self.bus_out

                bus_in.rx.signal.connect(bus_out.rx.signal)
                bus_in.tx.signal.connect(bus_out.tx.signal)
                bus_in.rx.reference.connect(bus_out.rx.reference)

        app = UARTBuffer()

        self.assertTrue(app.bus_in.rx.is_connected_to(app.bus_out.rx))
        self.assertTrue(app.bus_in.tx.is_connected_to(app.bus_out.tx))
        self.assertTrue(app.bus_in.is_connected_to(app.bus_out))

    def test_chains(self):
        mifs = times(3, ModuleInterface)
        mifs[0].connect(mifs[1])
        mifs[1].connect(mifs[2])
        self.assertTrue(mifs[0].is_connected_to(mifs[2]))

        mifs = times(3, ModuleInterface)
        mifs[0].connect_shallow(mifs[1])
        mifs[1].connect_shallow(mifs[2])
        self.assertTrue(mifs[0].is_connected_to(mifs[2]))
        self.assertIsInstance(mifs[0].is_connected_to(mifs[2]), _TLinkDirectShallow)

        mifs = times(3, ModuleInterface)
        mifs[0].connect_shallow(mifs[1])
        mifs[1].connect(mifs[2])
        self.assertTrue(mifs[0].is_connected_to(mifs[2]))
        self.assertIsInstance(mifs[0].is_connected_to(mifs[2]), _TLinkDirectShallow)

        # Test hierarchy down filter & chain resolution
        mifs = times(3, F.ElectricLogic)
        mifs[0].connect_shallow(mifs[1])
        mifs[1].connect(mifs[2])
        self.assertTrue(mifs[0].is_connected_to(mifs[2]))
        self.assertIsInstance(mifs[0].is_connected_to(mifs[2]), _TLinkDirectShallow)

        self.assertTrue(mifs[1].signal.is_connected_to(mifs[2].signal))
        self.assertTrue(mifs[1].reference.is_connected_to(mifs[2].reference))
        self.assertFalse(mifs[0].signal.is_connected_to(mifs[1].signal))
        self.assertFalse(mifs[0].reference.is_connected_to(mifs[1].reference))
        self.assertFalse(mifs[0].signal.is_connected_to(mifs[2].signal))
        self.assertFalse(mifs[0].reference.is_connected_to(mifs[2].reference))

        # Test duplicate resolution
        mifs[0].signal.connect(mifs[1].signal)
        mifs[0].reference.connect(mifs[1].reference)
        self.assertIsInstance(mifs[0].is_connected_to(mifs[1]), LinkDirect)
        self.assertIsInstance(mifs[0].is_connected_to(mifs[2]), LinkDirect)

    def test_bridge(self):
        self_ = self

        # U1 ---> _________B________ ---> U2
        #  TX          IL ===> OL          TX
        #   S -->  I -> S       S -> O -->  S
        #   R --------  R ----- R --------  R

        class Buffer(Module):
            ins = L.list_field(2, F.Electrical)
            outs = L.list_field(2, F.Electrical)

            ins_l = L.list_field(2, F.ElectricLogic)
            outs_l = L.list_field(2, F.ElectricLogic)

            def __preinit__(self) -> None:
                self_.assertIs(
                    self.ins_l[0].reference,
                    self.ins_l[0].single_electric_reference.get_reference(),
                )

                for el, lo in chain(
                    zip(self.ins, self.ins_l),
                    zip(self.outs, self.outs_l),
                ):
                    lo.signal.connect(el)

                for l1, l2 in zip(self.ins_l, self.outs_l):
                    l1.connect_shallow(l2)

            @L.rt_field
            def single_electric_reference(self):
                return F.has_single_electric_reference_defined(
                    F.ElectricLogic.connect_all_module_references(self)
                )

        class UARTBuffer(Module):
            buf: Buffer
            bus_in: F.UART_Base
            bus_out: F.UART_Base

            def __preinit__(self) -> None:
                bus1 = self.bus_in
                bus2 = self.bus_out
                buf = self.buf

                bus1.tx.signal.connect(buf.ins[0])
                bus1.rx.signal.connect(buf.ins[1])
                bus2.tx.signal.connect(buf.outs[0])
                bus2.rx.signal.connect(buf.outs[1])

            @L.rt_field
            def single_electric_reference(self):
                return F.has_single_electric_reference_defined(
                    F.ElectricLogic.connect_all_module_references(self)
                )

        import faebryk.core.core as c

        # Enable to see the stack trace of invalid connections
        # c.LINK_TB = True
        app = UARTBuffer()

        def _assert_no_link(mif1, mif2):
            link = mif1.is_connected_to(mif2)
            err = ""
            if link and c.LINK_TB:
                err = "\n" + print_stack(link.tb)
            self.assertFalse(link, err)

        def _assert_link(mif1: ModuleInterface, mif2: ModuleInterface, link=None):
            out = mif1.is_connected_to(mif2)
            if link:
                self.assertIsInstance(out, link)
                return
            self.assertIsNotNone(out)

        bus1 = app.bus_in
        bus2 = app.bus_out
        buf = app.buf

        # Check that the two buffer sides are not connected electrically
        _assert_no_link(buf.ins[0], buf.outs[0])
        _assert_no_link(buf.ins[1], buf.outs[1])
        _assert_no_link(bus1.rx.signal, bus2.rx.signal)
        _assert_no_link(bus1.tx.signal, bus2.tx.signal)

        # direct connect
        _assert_link(bus1.tx.signal, buf.ins[0])
        _assert_link(bus1.rx.signal, buf.ins[1])
        _assert_link(bus2.tx.signal, buf.outs[0])
        _assert_link(bus2.rx.signal, buf.outs[1])

        # connect through trait
        self.assertIs(
            buf.ins_l[0].single_electric_reference.get_reference(),
            buf.ins_l[0].reference,
        )
        _assert_link(buf.ins_l[0].reference, buf.outs_l[0].reference)
        _assert_link(buf.outs_l[1].reference, buf.ins_l[0].reference)
        _assert_link(bus1.rx.reference, bus2.rx.reference, LinkDirect)

        # connect through up
        _assert_link(bus1.tx, buf.ins_l[0], LinkDirect)
        _assert_link(bus2.tx, buf.outs_l[0], LinkDirect)

        # connect shallow
        _assert_link(buf.ins_l[0], buf.outs_l[0], _TLinkDirectShallow)

        # Check that the two buffer sides are connected logically
        _assert_link(bus1.tx, bus2.tx)
        _assert_link(bus1.rx, bus2.rx)
        _assert_link(bus1, bus2)

    def test_specialize(self):
        class Specialized(ModuleInterface): ...

        # general connection -> specialized connection
        mifs = times(3, ModuleInterface)
        mifs_special = times(3, Specialized)

        mifs[0].connect(mifs[1])
        mifs[1].connect(mifs[2])

        mifs[0].specialize(mifs_special[0])
        mifs[2].specialize(mifs_special[2])

        self.assertTrue(mifs_special[0].is_connected_to(mifs_special[2]))

        # specialized connection -> general connection
        mifs = times(3, ModuleInterface)
        mifs_special = times(3, Specialized)

        mifs_special[0].connect(mifs_special[1])
        mifs_special[1].connect(mifs_special[2])

        mifs[0].specialize(mifs_special[0])
        mifs[2].specialize(mifs_special[2])

        self.assertTrue(mifs[0].is_connected_to(mifs[2]))

        # test special link
        class _Link(LinkDirectShallow(lambda link, gif: True)): ...

        mifs = times(3, ModuleInterface)
        mifs_special = times(3, Specialized)

        mifs[0].connect(mifs[1], linkcls=_Link)
        mifs[1].connect(mifs[2])

        mifs[0].specialize(mifs_special[0])
        mifs[2].specialize(mifs_special[2])

        self.assertIsInstance(mifs_special[0].is_connected_to(mifs_special[2]), _Link)

    def test_isolated_connect(self):
        x1 = F.ElectricLogic()
        x2 = F.ElectricLogic()
        x1.connect(x2, linkcls=F.ElectricLogic.LinkIsolatedReference)
        self.assertIsInstance(
            x1.is_connected_to(x2), F.ElectricLogic.LinkIsolatedReference
        )

        self.assertIsInstance(
            x1.signal.is_connected_to(x2.signal),
            F.ElectricLogic.LinkIsolatedReference,
        )

        self.assertIsNone(x1.reference.is_connected_to(x2.reference))

        self.assertIsNone(x1.reference.hv.is_connected_to(x2.reference.hv))

        y1 = F.ElectricPower()
        y2 = F.ElectricPower()

        y1.make_source()
        y2.make_source()

        with self.assertRaises(F.Power.PowerSourcesShortedError):
            y1.connect(y2)

        ldo1 = F.LDO()
        ldo2 = F.LDO()

        with self.assertRaises(F.Power.PowerSourcesShortedError):
            ldo1.power_out.connect(ldo2.power_out)

        a1 = F.I2C()
        b1 = F.I2C()

        a1.connect(b1, linkcls=F.ElectricLogic.LinkIsolatedReference)
        self.assertIsInstance(
            a1.is_connected_to(b1), F.ElectricLogic.LinkIsolatedReference
        )
        self.assertIsInstance(
            a1.scl.signal.is_connected_to(b1.scl.signal),
            F.ElectricLogic.LinkIsolatedReference,
        )
        self.assertIsInstance(
            a1.sda.signal.is_connected_to(b1.sda.signal),
            F.ElectricLogic.LinkIsolatedReference,
        )

        self.assertIsNone(a1.scl.reference.is_connected_to(b1.scl.reference))
        self.assertIsNone(a1.sda.reference.is_connected_to(b1.sda.reference))


if __name__ == "__main__":
    unittest.main()
