# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import unittest
from itertools import chain

from faebryk.core.core import (
    LinkDirect,
    LinkDirectShallow,
    Module,
    ModuleInterface,
    _TLinkDirectShallow,
)
from faebryk.core.core import logger as core_logger
from faebryk.core.util import specialize_interface
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricLogic import ElectricLogic
from faebryk.library.has_single_electric_reference_defined import (
    has_single_electric_reference_defined,
)
from faebryk.library.UART_Base import UART_Base
from faebryk.libs.util import print_stack, times

logger = logging.getLogger(__name__)
core_logger.setLevel(logger.getEffectiveLevel())


class TestHierarchy(unittest.TestCase):
    def test_up_connect(self):
        class UARTBuffer(Module):
            def __init__(self) -> None:
                super().__init__()

                class _IFs(super().IFS()):
                    bus_in = UART_Base()
                    bus_out = UART_Base()

                self.IFs = _IFs(self)

                bus_in = self.IFs.bus_in
                bus_out = self.IFs.bus_out

                bus_in.IFs.rx.IFs.signal.connect(bus_out.IFs.rx.IFs.signal)
                bus_in.IFs.tx.IFs.signal.connect(bus_out.IFs.tx.IFs.signal)
                bus_in.IFs.rx.IFs.reference.connect(bus_out.IFs.rx.IFs.reference)

        app = UARTBuffer()

        self.assertTrue(app.IFs.bus_in.IFs.rx.is_connected_to(app.IFs.bus_out.IFs.rx))
        self.assertTrue(app.IFs.bus_in.IFs.tx.is_connected_to(app.IFs.bus_out.IFs.tx))
        self.assertTrue(app.IFs.bus_in.is_connected_to(app.IFs.bus_out))

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
        mifs = times(3, ElectricLogic)
        mifs[0].connect_shallow(mifs[1])
        mifs[1].connect(mifs[2])
        self.assertTrue(mifs[0].is_connected_to(mifs[2]))
        self.assertIsInstance(mifs[0].is_connected_to(mifs[2]), _TLinkDirectShallow)

        self.assertTrue(mifs[1].IFs.signal.is_connected_to(mifs[2].IFs.signal))
        self.assertTrue(mifs[1].IFs.reference.is_connected_to(mifs[2].IFs.reference))
        self.assertFalse(mifs[0].IFs.signal.is_connected_to(mifs[1].IFs.signal))
        self.assertFalse(mifs[0].IFs.reference.is_connected_to(mifs[1].IFs.reference))
        self.assertFalse(mifs[0].IFs.signal.is_connected_to(mifs[2].IFs.signal))
        self.assertFalse(mifs[0].IFs.reference.is_connected_to(mifs[2].IFs.reference))

        # Test duplicate resolution
        mifs[0].IFs.signal.connect(mifs[1].IFs.signal)
        mifs[0].IFs.reference.connect(mifs[1].IFs.reference)
        self.assertIsInstance(mifs[0].is_connected_to(mifs[1]), LinkDirect)
        self.assertIsInstance(mifs[0].is_connected_to(mifs[2]), LinkDirect)

    def test_bridge(self):
        class Buffer(Module):
            def __init__(self) -> None:
                super().__init__()

                class _IFs(super().IFS()):
                    ins = times(2, Electrical)
                    outs = times(2, Electrical)

                    ins_l = times(2, ElectricLogic)
                    outs_l = times(2, ElectricLogic)

                self.IFs = _IFs(self)

                ref = ElectricLogic.connect_all_module_references(self)
                self.add_trait(has_single_electric_reference_defined(ref))

                for el, lo in chain(
                    zip(self.IFs.ins, self.IFs.ins_l),
                    zip(self.IFs.outs, self.IFs.outs_l),
                ):
                    lo.IFs.signal.connect(el)

                for l1, l2 in zip(self.IFs.ins_l, self.IFs.outs_l):
                    l1.connect_shallow(l2)

        class UARTBuffer(Module):
            def __init__(self) -> None:
                super().__init__()

                class _NODES(super().NODES()):
                    buf = Buffer()

                class _IFs(super().IFS()):
                    bus_in = UART_Base()
                    bus_out = UART_Base()

                self.IFs = _IFs(self)
                self.NODEs = _NODES(self)

                ElectricLogic.connect_all_module_references(self)

                bus1 = self.IFs.bus_in
                bus2 = self.IFs.bus_out
                buf = self.NODEs.buf

                bus1.IFs.tx.IFs.signal.connect(buf.IFs.ins[0])
                bus1.IFs.rx.IFs.signal.connect(buf.IFs.ins[1])
                bus2.IFs.tx.IFs.signal.connect(buf.IFs.outs[0])
                bus2.IFs.rx.IFs.signal.connect(buf.IFs.outs[1])

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

        bus1 = app.IFs.bus_in
        bus2 = app.IFs.bus_out
        buf = app.NODEs.buf

        # Check that the two buffer sides are not connected electrically
        _assert_no_link(buf.IFs.ins[0], buf.IFs.outs[0])
        _assert_no_link(buf.IFs.ins[1], buf.IFs.outs[1])
        _assert_no_link(bus1.IFs.rx.IFs.signal, bus2.IFs.rx.IFs.signal)
        _assert_no_link(bus1.IFs.tx.IFs.signal, bus2.IFs.tx.IFs.signal)

        # Check that the two buffer sides are connected logically
        self.assertTrue(bus1.IFs.rx.is_connected_to(bus2.IFs.rx))
        self.assertTrue(bus1.IFs.tx.is_connected_to(bus2.IFs.tx))
        self.assertTrue(bus1.is_connected_to(bus2))

    def test_specialize(self):
        class Specialized(ModuleInterface): ...

        # general connection -> specialized connection
        mifs = times(3, ModuleInterface)
        mifs_special = times(3, Specialized)

        mifs[0].connect(mifs[1])
        mifs[1].connect(mifs[2])

        specialize_interface(mifs[0], mifs_special[0])
        specialize_interface(mifs[2], mifs_special[2])

        self.assertTrue(mifs_special[0].is_connected_to(mifs_special[2]))

        # specialized connection -> general connection
        mifs = times(3, ModuleInterface)
        mifs_special = times(3, Specialized)

        mifs_special[0].connect(mifs_special[1])
        mifs_special[1].connect(mifs_special[2])

        specialize_interface(mifs[0], mifs_special[0])
        specialize_interface(mifs[2], mifs_special[2])

        self.assertTrue(mifs[0].is_connected_to(mifs[2]))

        # test special link
        class _Link(LinkDirectShallow(lambda link, gif: True)): ...

        mifs = times(3, ModuleInterface)
        mifs_special = times(3, Specialized)

        mifs[0].connect(mifs[1], linkcls=_Link)
        mifs[1].connect(mifs[2])

        specialize_interface(mifs[0], mifs_special[0])
        specialize_interface(mifs[2], mifs_special[2])

        self.assertIsInstance(mifs_special[0].is_connected_to(mifs_special[2]), _Link)


if __name__ == "__main__":
    unittest.main()
