# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from itertools import chain, pairwise

import pytest

import faebryk.library._F as F
from faebryk.core.link import (
    LinkDirect,
    LinkDirectConditional,
    LinkDirectConditionalFilterResult,
    LinkDirectDerived,
)
from faebryk.core.module import Module
from faebryk.core.moduleinterface import IMPLIED_PATHS, ModuleInterface
from faebryk.core.node import NodeException
from faebryk.libs.app.erc import (
    ERCFaultShortedModuleInterfaces,
    ERCPowerSourcesShortedError,
    simple_erc,
)
from faebryk.libs.library import L
from faebryk.libs.util import cast_assert, times
from test.common.resources.fabll_modules.ButtonCell import ButtonCell
from test.common.resources.fabll_modules.RP2040 import RP2040
from test.common.resources.fabll_modules.RP2040_ReferenceDesign import (
    RP2040_ReferenceDesign,
)

logger = logging.getLogger(__name__)


def test_self():
    mif = ModuleInterface()
    assert mif.is_connected_to(mif)


def test_up_connect_simple_single():
    """
    ```
    H1      H2
     L1 -->  L1
    ```
    """

    class High(ModuleInterface):
        lower: ModuleInterface

    high1 = High()
    high2 = High()

    high1.lower.connect(high2.lower)
    assert high1.is_connected_to(high2)


def test_up_connect_simple_two():
    """
    ```
    H1      H2
     L1 -->  L1
     L2 -->  L2
    ```
    """

    class High(ModuleInterface):
        lower1: ModuleInterface
        lower2: ModuleInterface

    high1 = High()
    high2 = High()

    high1.lower1.connect(high2.lower1)
    high1.lower2.connect(high2.lower2)
    assert high1.is_connected_to(high2)


def test_up_connect_simple_multiple():
    """
    ```
    H1      H2
     L1 -->  L1
     L2 -->  L2
     L3 -->  L3
    ```
    """

    class High(ModuleInterface):
        lower1: ModuleInterface
        lower2: ModuleInterface
        lower3: ModuleInterface

    high1 = High()
    high2 = High()

    high1.lower1.connect(high2.lower1)
    high1.lower2.connect(high2.lower2)
    high1.lower3.connect(high2.lower3)
    assert high1.is_connected_to(high2)


def test_up_connect_chain_simple():
    """
    ```
    H1            H2
     L1 --> M -->  L1
     L2 -------->  L2
    ```
    """

    class High(ModuleInterface):
        lower1: ModuleInterface
        lower2: ModuleInterface

    high1 = High()
    high2 = High()

    middle = ModuleInterface()

    high1.lower1.connect(middle)
    high2.lower1.connect(middle)
    high1.lower2.connect(high2.lower2)

    assert high1.is_connected_to(high2)


def test_up_connect_chain_multiple_same():
    """
    ```
    H1      H2      H3
     L1 -->  L1 -->  L1
     L2 -->  L2 -->  L2
    ```
    """

    class High(ModuleInterface):
        lower1: ModuleInterface
        lower2: ModuleInterface

    high1 = High()
    high2 = High()
    high3 = High()

    high1.lower1.connect(high2.lower1)
    high1.lower2.connect(high2.lower2)
    high2.lower1.connect(high3.lower1)
    high2.lower2.connect(high3.lower2)

    assert high1.is_connected_to(high3)


def test_up_connect_chain_multiple_mixed():
    """
    ```
    H1      H2  ==>  H3      H4
     L1 -->  L1       L1 -->  L1
     L2 -->  L2       L2 -->  L2
    ```
    """

    class Low(ModuleInterface): ...

    class High(ModuleInterface):
        lower1: Low
        lower2: Low

    high1, high2, high3, high4 = times(4, High)

    high1.lower1.connect(high2.lower1)
    high1.lower2.connect(high2.lower2)
    high2.connect_shallow(high3)
    high3.lower1.connect(high4.lower1)
    high3.lower2.connect(high4.lower2)

    assert high1.is_connected_to(high4)


def test_split_chain_single():
    """
    Miro: Implied bus connection 2
    ```
    H1     H2 --> H3
     L1 --> L1     L1
     L2     L2     L2
      |             ^
      +-------------+
    ```
    """

    class Low(ModuleInterface): ...

    class High(ModuleInterface):
        lower1: Low
        lower2: Low

    high1, high2, high3 = times(3, High)

    high1.lower1.connect(high2.lower1)
    high1.lower2.connect(high3.lower2)
    high2.connect(high3)

    assert high1.is_connected_to(high3)


@pytest.mark.xfail(reason="No support atm for split chains with ambiguous split/hier")
def test_split_chain_double_flat_no_inter():
    """
    ```
    H1     H2 --> H3     H4
     L1 --> L1     L1 --> L1
     L2     L2     L2     L2
      |                    ^
      +--------------------+
    ```
    """

    class Low(ModuleInterface): ...

    class High(ModuleInterface):
        lower1: Low
        lower2: Low

    class App(Module):
        high = L.list_field(4, High)

    app = App()

    high1, high2, high3, high4 = app.high

    high1.lower1.connect(high2.lower1)
    high1.lower2.connect(high4.lower2)
    high2.connect(high3)
    high3.lower1.connect(high4.lower1)

    assert high1.lower1.is_connected_to(high4.lower1)
    x = high1.is_connected_to(high3)
    print(x)
    assert not x
    # assert not high1.is_connected_to(high3)
    assert high1.is_connected_to(high4)

    # TODO: See pathfinder.cpp:67 for failure


def test_split_chain_double_flat_inter():
    # TODO this test is not difficult enough
    # the intermediate is trivially connected since the double split is resolved
    # maybe insert extra node between H2 and H3?
    """
    ```
    H1     H2 --> H3     H4
     L1 --> L1     L1 --> L1
     L2     L2     L2 --> L2
      |                    ^
      +--------------------+
    ```
    """

    class Low(ModuleInterface): ...

    class High(ModuleInterface):
        lower1: Low
        lower2: Low

    class App(Module):
        high = L.list_field(4, High)

    app = App()

    high1, high2, high3, high4 = app.high

    high1.lower1.connect(high2.lower1)
    high1.lower2.connect(high4.lower2)
    high2.connect(high3)
    high3.lower1.connect(high4.lower1)
    high3.lower2.connect(high4.lower2)

    assert high1.lower1.is_connected_to(high4.lower1)
    assert high1.is_connected_to(high3)
    assert high1.is_connected_to(high4)


@pytest.mark.xfail(reason="No support atm for split chains with ambiguous split/hier")
def test_split_chain_double_hierarchy():
    """
    ```
                 R1 --> R2
    H1     H2 --> H      H      H3
     L1 --> L1     L1     L1 --> L1
     L2     L2     L2     L2     L2
      |                           ^
      +---------------------------+
    ```
    """

    class Low(ModuleInterface): ...

    class High(ModuleInterface):
        lower1: Low
        lower2: Low

    class Higher(ModuleInterface):
        high: High

    class App(Module):
        high = L.list_field(3, High)
        higher = L.list_field(2, Higher)

    app = App()

    high1, high2, high3 = app.high
    higher1, higher2 = app.higher

    high1.lower1.connect(higher1.high.lower1)
    high1.lower2.connect(high3.lower2)
    high2.connect(higher1.high)
    higher1.connect_shallow(higher2)
    higher2.high.lower1.connect(high3.lower1)

    assert high1.lower1.is_connected_to(high3.lower1)
    assert high1.is_connected_to(high3)


def test_split_chain_flip():
    """
    Miro: Implied Double-Flip Bus Connection
    ```
    H1     H2 ==> H3     H4
     L1 --> L2     L2 --> L1
     L2 --> L1     L1 --> L2
    ```
    Note: Shallowness not important, just makes it harder
    """

    class Low(ModuleInterface): ...

    class High(ModuleInterface):
        lower1: Low
        lower2: Low

    class App(Module):
        high = L.list_field(4, High)

    app = App()

    high1, high2, high3, high4 = app.high

    high1.lower1.connect(high2.lower2)
    high1.lower2.connect(high2.lower1)
    high2.connect_shallow(high3)
    high3.lower1.connect(high4.lower2)
    high3.lower2.connect(high4.lower1)

    assert high1.is_connected_to(high4)


def test_split_flip_negative():
    """
    Miro: Implied Bus Non-Connection
    ```
    H1     H2
     L1 --> L2
     L2 --> L1
    ```
    """

    class Low(ModuleInterface): ...

    class High(ModuleInterface):
        lower1: Low
        lower2: Low

    high1, high2 = times(2, High)

    high1.lower1.connect(high2.lower2)
    high1.lower2.connect(high2.lower1)

    assert not high1.is_connected_to(high2)


def test_up_connect_chain_multiple_mixed_simulate_realworld():
    """
    ```
    H1      H2  ==>  H3      H4
     L1 -->  L1       L1 -->  L1
     L2 ---  L2 ----- L2 ---  L2
    ```
    """

    class Low(ModuleInterface): ...

    class High(ModuleInterface):
        lower1: Low
        lower2: Low

    high1, high2, high3, high4 = times(4, High)

    high1.lower1.connect(high2.lower1)
    high2.connect_shallow(high3)
    high3.lower1.connect(high4.lower1)

    high1.lower2.connect(high2.lower2, high3.lower2, high4.lower2)

    assert high1.is_connected_to(high4)


@pytest.mark.xfail(reason="No support atm for split chains with ambiguous split/hier")
def test_up_connect_chain_multiple_realworld():
    """
    ```
    L1      L2 ==>  L3     L4
     S -->  S       S -->  S
     R ---  R ----- R ---  R
      HV     HV      HV     HV
      LV     LV      LV     LV
    ```
    """

    l1, l2, l3, l4 = times(4, F.ElectricLogic)

    l1.signal.connect(l2.signal)
    l2.connect_shallow(l3)
    l3.signal.connect(l4.signal)

    l1.reference.connect(l2.reference, l3.reference, l4.reference)

    assert l1.is_connected_to(l4)


def test_up_connect_chain_hierarchy():
    """
    ```
    R1              R2
     H1     HM1 ==>  H1
      L1 -->  L1      L1
      L2 -->  L2      L2
     H2 ==> HM2      H2
      L1      L1 -->  L1
      L2      L2 -->  L2
    ```
    """

    class Low(ModuleInterface): ...

    class High(ModuleInterface):
        lower1: Low
        lower2: Low

    class Higher(ModuleInterface):
        high1: High
        high2: High

    higher_begin = Higher()
    higher_end = Higher()

    high_middle1 = High()
    high_middle2 = High()

    higher_begin.high1.lower1.connect(high_middle1.lower1)
    higher_begin.high1.lower2.connect(high_middle1.lower2)
    higher_begin.high2.connect_shallow(high_middle2)
    higher_end.high1.connect_shallow(high_middle1)
    higher_end.high2.lower1.connect(high_middle2.lower1)
    higher_end.high2.lower2.connect(high_middle2.lower2)

    assert higher_begin.is_connected_to(higher_end)


def test_up_connect_hierarchy():
    """
    ```
    R1      R2
     H1      H1
      L1 -->  L1
      L2 -->  L2
     H2      H2
      L1 -->  L1
      L2 -->  L2
    ```
    """

    class High(ModuleInterface):
        lower1: ModuleInterface
        lower2: ModuleInterface

    class Higher(ModuleInterface):
        high1: High
        high2: High

    higher1 = Higher()
    higher2 = Higher()

    higher1.high1.lower1.connect(higher2.high1.lower1)
    higher1.high1.lower2.connect(higher2.high1.lower2)
    higher1.high2.lower1.connect(higher2.high2.lower1)
    higher1.high2.lower2.connect(higher2.high2.lower2)
    assert higher1.is_connected_to(higher2)


def test_up_connect_hierarchy_mixed():
    """
    ```
    R1      R2
     H1      H1
      L1 -->  L1
      L2 -->  L2
     H2 ==>  H2
      L1      L1
      L2      L2
    ```
    """

    class Low(ModuleInterface): ...

    class High(ModuleInterface):
        lower1: Low
        lower2: Low

    class Higher(ModuleInterface):
        high1: High
        high2: High

    higher1 = Higher()
    higher2 = Higher()

    higher1.high1.lower1.connect(higher2.high1.lower1)
    higher1.high1.lower2.connect(higher2.high1.lower2)
    higher1.high2.connect_shallow(higher2.high2)
    assert higher1.is_connected_to(higher2)


def test_up_connect_simple_two_negative():
    """
    ```
    H1      H2
     L1 -->  L1
     L2      L2
    ```
    """

    class High(ModuleInterface):
        lower1: ModuleInterface
        lower2: ModuleInterface

    high1 = High()
    high2 = High()

    high1.lower1.connect(high2.lower1)
    assert not high1.is_connected_to(high2)


def test_up_connect_simple_multiple_negative():
    """
    ```
    H1      H2
     L1 -->  L1
     L2 -->  L2
     L3      L3
    ```
    """

    class High(ModuleInterface):
        lower1: ModuleInterface
        lower2: ModuleInterface
        lower3: ModuleInterface

    high1 = High()
    high2 = High()

    high1.lower1.connect(high2.lower1)
    high1.lower2.connect(high2.lower2)
    assert not high1.is_connected_to(high2)


def test_up_connect():
    """
    ```
    BI     BO
     RX      RX
      S -->  S
      R -->  R
       HV      HV
       LV      LV
     TX      TX
      S -->  S
      R -->  R
       HV      HV
       LV      LV
    ```
    """

    class UARTBuffer(Module):
        bus_in: F.UART_Base
        bus_out: F.UART_Base

        def __preinit__(self) -> None:
            self.bus_in.rx.line.connect(self.bus_out.rx.line)
            self.bus_in.tx.line.connect(self.bus_out.tx.line)
            self.bus_in.rx.reference.connect(self.bus_out.rx.reference)

    app = UARTBuffer()

    assert app.bus_in.rx.line.is_connected_to(app.bus_out.rx.line)
    assert app.bus_in.rx.reference.is_connected_to(app.bus_out.rx.reference)
    assert app.bus_in.rx.is_connected_to(app.bus_out.rx)
    assert app.bus_in.tx.is_connected_to(app.bus_out.tx)
    assert app.bus_in.is_connected_to(app.bus_out)


def test_down_connect():
    """
    ```
    P1 -->  P2
     HV      HV
     LV      LV
    ```
    """

    ep = times(2, F.ElectricPower)
    ep[0].connect(ep[1])

    assert ep[0].is_connected_to(ep[1])
    assert ep[0].hv.is_connected_to(ep[1].hv)
    assert ep[0].lv.is_connected_to(ep[1].lv)


def test_chains_direct():
    """
    ```
    M1 --> M2 --> M3
    ```
    """

    mifs = times(3, ModuleInterface)
    mifs[0].connect(mifs[1])
    mifs[1].connect(mifs[2])
    assert mifs[0].is_connected_to(mifs[2])


def test_chains_double_shallow_flat():
    """
    ```
    M1 ==> M2 ==> M3
    ```
    """

    mifs = times(3, ModuleInterface)
    mifs[0].connect_shallow(mifs[1])
    mifs[1].connect_shallow(mifs[2])
    assert mifs[0].is_connected_to(mifs[2])


def test_chains_mixed_shallow_flat():
    """
    ```
    M1 ==> M2 --> M3
    ```
    """

    mifs = times(3, ModuleInterface)
    mifs[0].connect_shallow(mifs[1])
    mifs[1].connect(mifs[2])
    assert mifs[0].is_connected_to(mifs[2])


def test_chains_mixed_shallow_nested():
    """
    ```
    L1  ==>  L2 -->  L3
     S        S       S
     R        R       R
      HV       HV      HV
      LV       LV      LV
    ```
    """
    # Test hierarchy down filter & chain resolution
    el = times(3, F.ElectricLogic)
    el[0].connect_shallow(el[1])
    el[1].connect(el[2])
    assert el[0].is_connected_to(el[2])

    assert el[1].line.is_connected_to(el[2].line)
    assert el[1].reference.is_connected_to(el[2].reference)
    assert not el[0].line.is_connected_to(el[1].line)
    assert not el[0].reference.is_connected_to(el[1].reference)
    assert not el[0].line.is_connected_to(el[2].line)
    assert not el[0].reference.is_connected_to(el[2].reference)

    # Test duplicate resolution
    el[0].line.connect(el[1].line)
    el[0].reference.connect(el[1].reference)
    assert el[0].is_connected_to(el[1])
    assert el[0].is_connected_to(el[2])


def test_loooooong_chain():
    """Let's make it hard"""
    mifs = times(2**10, F.ElectricPower)
    for left, right in pairwise(mifs):
        left.connect(right)

    assert mifs[0].is_connected_to(mifs[-1])


# FIXME: this should be WAYYY higher than 16
@pytest.mark.parametrize("length", [16])
def test_alternating_long_chain(length):
    """Let's make it hard"""
    mifs = times(length, F.ElectricPower)
    for i, (left, right) in enumerate(pairwise(mifs)):
        if i % 2:
            left.connect(right)
        else:
            left.lv.connect(right.lv)
            left.hv.connect(right.hv)

    assert mifs[0].is_connected_to(mifs[-1])
    assert mifs[0].lv.is_connected_to(mifs[-1].lv)
    assert mifs[0].hv.is_connected_to(mifs[-1].hv)


def test_shallow_bridge_simple():
    """
    ```
                B
    H1      HI ===> HO     H2
     L1 -->  L1      L1 --> L1
     L2 -->  L2      L2 --> L2
    ```
    """

    class Low(ModuleInterface): ...

    class High(ModuleInterface):
        lower1: Low
        lower2: Low

    class ShallowBridge(Module):
        high_in: High
        high_out: High

        def __preinit__(self) -> None:
            self.high_in.connect_shallow(self.high_out)

        @L.rt_field
        def can_bridge(self):
            return F.can_bridge_defined(self.high_in, self.high_out)

    bridge = ShallowBridge()
    high1 = High()
    high2 = High()
    high1.connect_via(bridge, high2)

    assert high1.is_connected_to(high2)
    assert not bridge.high_in.lower1.is_connected_to(bridge.high_out.lower1)
    assert not bridge.high_in.lower2.is_connected_to(bridge.high_out.lower2)
    assert not high1.lower1.is_connected_to(high2.lower1)
    assert not high1.lower2.is_connected_to(high2.lower2)


@pytest.mark.xfail(reason="No support atm for split chains with ambiguous split/hier")
def test_shallow_bridge_partial():
    """
    ```
             ________B__________
     L1          LI ===> LO          L2
      S -->  I -> S       S -> O -->  S
      R --------  R ----- R --------  R
    ```
    """

    class Buffer(Module):
        ins: F.Electrical
        outs: F.Electrical

        ins_l: F.ElectricLogic
        outs_l: F.ElectricLogic

        def __preinit__(self) -> None:
            self.ins_l.signal.connect(self.ins)
            self.outs_l.signal.connect(self.outs)

            self.ins_l.connect_shallow(self.outs_l)

        @L.rt_field
        def single_electric_reference(self):
            return F.has_single_electric_reference_defined(
                F.ElectricLogic.connect_all_module_references(self)
            )

    l1 = F.ElectricLogic()
    l2 = F.ElectricLogic()
    b = Buffer()

    l1.signal.connect(b.ins)
    l2.signal.connect(b.outs)
    l1.reference.connect(b.single_electric_reference.get_reference())
    l2.reference.connect(b.single_electric_reference.get_reference())

    assert l1.is_connected_to(l2)


def test_shallow_bridge_full():
    """
    Test the bridge connection between two UART interfaces through a buffer:

    ```
    U1 ---> _________B________ ---> U2
     TX          LI ===> LO          TX
      S -->  I -> S       S -> O -->  S
      R --------  R ----- R --------  R
    ```

    Where:
    - U1, U2: UART interfaces
    - B: Buffer
    - TX: Transmit
    - S: Signal
    - R: Reference
    - I: Input
    - O: Output
    - IL: Input Logic
    - OL: Output Logic
    """

    class Buffer(Module):
        ins = L.list_field(2, F.Electrical)
        outs = L.list_field(2, F.Electrical)

        ins_l = L.list_field(2, F.ElectricLogic)
        outs_l = L.list_field(2, F.ElectricLogic)

        def __preinit__(self) -> None:
            assert (
                self.ins_l[0].reference
                is self.ins_l[0].single_electric_reference.get_reference()
            )

            for el, lo in chain(
                zip(self.ins, self.ins_l),
                zip(self.outs, self.outs_l),
            ):
                lo.line.connect(el)

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
            bus_i = self.bus_in
            bus_o = self.bus_out
            buf = self.buf

            bus_i.tx.line.connect(buf.ins[0])
            bus_i.rx.line.connect(buf.ins[1])
            bus_o.tx.line.connect(buf.outs[0])
            bus_o.rx.line.connect(buf.outs[1])

        @L.rt_field
        def single_electric_reference(self):
            return F.has_single_electric_reference_defined(
                F.ElectricLogic.connect_all_module_references(self)
            )

    app = UARTBuffer()

    bus_i = app.bus_in
    bus_o = app.bus_out
    buf = app.buf

    # Check that the two buffer sides are not connected electrically
    assert not buf.ins[0].is_connected_to(buf.outs[0])
    assert not buf.ins[1].is_connected_to(buf.outs[1])
    assert not bus_i.rx.line.is_connected_to(bus_o.rx.line)
    assert not bus_i.tx.line.is_connected_to(bus_o.tx.line)

    # direct connect
    assert bus_i.tx.line.is_connected_to(buf.ins[0])
    assert bus_i.rx.line.is_connected_to(buf.ins[1])
    assert bus_o.tx.line.is_connected_to(buf.outs[0])
    assert bus_o.rx.line.is_connected_to(buf.outs[1])

    # connect through trait
    assert (
        buf.ins_l[0].single_electric_reference.get_reference() is buf.ins_l[0].reference
    )
    assert buf.ins_l[0].reference.is_connected_to(buf.outs_l[0].reference)
    assert buf.outs_l[1].reference.is_connected_to(buf.ins_l[0].reference)
    assert bus_i.rx.reference.is_connected_to(bus_o.rx.reference)

    # connect through up
    assert bus_i.tx.is_connected_to(buf.ins_l[0])
    assert bus_o.tx.is_connected_to(buf.outs_l[0])

    # connect shallow
    assert buf.ins_l[0].is_connected_to(buf.outs_l[0])

    # Check that the two buffer sides are connected logically
    assert bus_i.tx.is_connected_to(bus_o.tx)
    assert bus_i.rx.is_connected_to(bus_o.rx)
    assert bus_i.is_connected_to(bus_o)


class Specialized(ModuleInterface): ...


class DoubleSpecialized(Specialized): ...


def test_specialize_general_to_special():
    # general connection -> specialized connection
    mifs = times(3, ModuleInterface)
    mifs_special = times(3, Specialized)

    mifs[0].connect(mifs[1])
    mifs[1].connect(mifs[2])

    mifs[0].specialize(mifs_special[0])
    mifs[2].specialize(mifs_special[2])

    assert mifs_special[0].is_connected_to(mifs_special[2])


def test_specialize_special_to_general():
    # specialized connection -> general connection
    mifs = times(3, ModuleInterface)
    mifs_special = times(3, Specialized)

    mifs_special[0].connect(mifs_special[1])
    mifs_special[1].connect(mifs_special[2])

    mifs[0].specialize(mifs_special[0])
    mifs[2].specialize(mifs_special[2])

    assert mifs[0].is_connected_to(mifs[2])


def test_specialize_link():
    # test special link
    class _Link(LinkDirectConditional):
        def __init__(self):
            super().__init__(
                lambda path: LinkDirectConditionalFilterResult.FILTER_PASS,
                needs_only_first_in_path=True,
            )

    mifs = times(3, ModuleInterface)
    mifs_special = times(3, Specialized)

    mifs[0].connect(mifs[1], link=_Link)
    mifs[1].connect(mifs[2])

    mifs[0].specialize(mifs_special[0])
    mifs[2].specialize(mifs_special[2])

    assert mifs_special[0].is_connected_to(mifs_special[2])


def test_specialize_double_with_gap():
    # double specialization with gap
    mifs = times(2, ModuleInterface)
    mifs_special = times(1, Specialized)
    mifs_double_special = times(2, DoubleSpecialized)

    mifs[0].connect(mifs[1])
    mifs[0].specialize(mifs_special[0])
    mifs_special[0].specialize(mifs_double_special[0])
    mifs[1].specialize(mifs_double_special[1])

    assert mifs_double_special[0].is_connected_to(mifs_double_special[1])


def test_specialize_double_with_gap_2():
    mifs = times(2, ModuleInterface)
    mifs_special = times(1, Specialized)
    mifs_double_special = times(2, DoubleSpecialized)

    mifs_double_special[0].connect(mifs_double_special[1])
    mifs[0].specialize(mifs_special[0])
    mifs_special[0].specialize(mifs_double_special[0])
    mifs[1].specialize(mifs_double_special[1])

    assert mifs[0].is_connected_to(mifs[1])


def test_specialize_module():
    battery = F.Battery()
    power = F.ElectricPower()

    battery.power.connect(power)
    buttoncell = battery.specialize(ButtonCell())

    assert buttoncell.power.is_connected_to(battery.power)
    assert power.is_connected_to(buttoncell.power)


def test_isolated_connect_simple():
    x1 = F.ElectricLogic()
    x2 = F.ElectricLogic()
    x1.connect(x2, link=F.ElectricLogic.LinkIsolatedReference)

    assert x1.is_connected_to(x2)
    assert x1.line.is_connected_to(x2.line)

    assert not x1.reference.is_connected_to(x2.reference)
    assert not x1.reference.hv.is_connected_to(x2.reference.hv)


def test_isolated_connect_erc():
    y1 = F.ElectricPower()
    y2 = F.ElectricPower()

    y1.make_source()
    y2.make_source()

    with pytest.raises(ERCPowerSourcesShortedError):
        y1.connect(y2)
        simple_erc(y1.get_graph())

    ldo1 = F.LDO()
    ldo2 = F.LDO()

    with pytest.raises(ERCPowerSourcesShortedError):
        ldo1.power_out.connect(ldo2.power_out)
        simple_erc(ldo1.get_graph())

    a1 = F.I2C()
    b1 = F.I2C()

    a1.connect(b1, link=F.ElectricLogic.LinkIsolatedReference)
    assert a1.is_connected_to(b1)
    assert a1.scl.line.is_connected_to(b1.scl.line)
    assert a1.sda.line.is_connected_to(b1.sda.line)

    assert not a1.scl.reference.is_connected_to(b1.scl.reference)
    assert not a1.sda.reference.is_connected_to(b1.sda.reference)


def test_simple_erc_ElectricPower_short():
    ep1 = F.ElectricPower()
    ep2 = F.ElectricPower()

    ep1.connect(ep2)

    # This is okay!
    simple_erc(ep1.get_graph())

    ep1.lv.connect(ep2.hv)

    # This is not okay!
    with pytest.raises(ERCFaultShortedModuleInterfaces) as ex:
        simple_erc(ep1.get_graph())

    assert set(ex.value.path) == {ep1.lv, ep2.hv}


@pytest.mark.skipif(not IMPLIED_PATHS, reason="IMPLIED_PATHS is not set")
def test_direct_implied_paths():
    powers = times(2, F.ElectricPower)

    # direct implied
    powers[0].connect(powers[1])

    assert powers[1].hv in powers[0].hv.get_connected()

    paths = powers[0].hv.is_connected_to(powers[1].hv)
    assert paths
    path = paths[0]
    assert len(path) == 4
    assert isinstance(path[1].is_connected_to(path[2]), LinkDirectDerived)


@pytest.mark.skipif(not IMPLIED_PATHS, reason="IMPLIED_PATHS is not set")
def test_children_implied_paths():
    powers = times(3, F.ElectricPower)

    # children implied
    powers[0].connect(powers[1])
    powers[1].hv.connect(powers[2].hv)
    powers[1].lv.connect(powers[2].lv)

    assert powers[2] in powers[0].get_connected()

    paths = list(powers[0].is_connected_to(powers[2]))
    assert paths
    assert len(paths[0]) == 4
    assert isinstance(paths[0][1].is_connected_to(paths[0][2]), LinkDirectDerived)


@pytest.mark.skipif(not IMPLIED_PATHS, reason="IMPLIED_PATHS is not set")
def test_shallow_implied_paths():
    powers = times(4, F.ElectricPower)

    # shallow implied
    powers[0].connect(powers[1])
    powers[1].hv.connect(powers[2].hv)
    powers[1].lv.connect(powers[2].lv)
    powers[2].connect_shallow(powers[3])

    assert powers[3] in powers[0].get_connected()

    assert not powers[0].hv.is_connected_to(powers[3].hv)


def test_direct_shallow_instance():
    class MIFType(ModuleInterface):
        pass

    mif1 = MIFType()
    mif2 = MIFType()
    mif3 = MIFType()

    mif1.connect_shallow(mif2, mif3)
    assert isinstance(
        mif1.connected.is_connected_to(mif2.connected), MIFType.LinkDirectShallow()
    )
    assert isinstance(
        mif1.connected.is_connected_to(mif3.connected), MIFType.LinkDirectShallow()
    )


def test_regression_rp2040_usb_diffpair_minimal():
    usb = F.USB2_0_IF.Data()
    terminated_usb = usb.terminated()

    other_usb = F.USB2_0_IF.Data()
    terminated_usb.connect(other_usb)

    n_ref = usb.n.reference
    p_ref = usb.p.reference
    t_n_ref = terminated_usb.n.reference
    t_p_ref = terminated_usb.p.reference
    o_n_ref = other_usb.n.reference
    o_p_ref = other_usb.p.reference
    refs = {n_ref, p_ref, t_n_ref, t_p_ref, o_n_ref, o_p_ref}

    assert isinstance(
        usb.connected.is_connected_to(terminated_usb.connected),
        F.USB2_0_IF.Data.LinkDirectShallow(),
    )
    assert isinstance(
        other_usb.connected.is_connected_to(terminated_usb.connected), LinkDirect
    )
    assert usb.connected.is_connected_to(other_usb.connected) is None

    connected_per_mif = {ref: ref.get_connected(include_self=True) for ref in refs}

    assert not {n_ref, p_ref} & connected_per_mif[t_n_ref].keys()
    assert not {n_ref, p_ref} & connected_per_mif[t_p_ref].keys()
    assert not {t_n_ref, t_p_ref} & connected_per_mif[n_ref].keys()
    assert not {t_n_ref, t_p_ref} & connected_per_mif[p_ref].keys()

    assert set(connected_per_mif[n_ref].keys()) == {n_ref, p_ref}
    assert set(connected_per_mif[p_ref].keys()) == {n_ref, p_ref}
    assert set(connected_per_mif[t_n_ref].keys()) == {
        t_n_ref,
        t_p_ref,
        o_n_ref,
        o_p_ref,
    }
    assert set(connected_per_mif[t_p_ref].keys()) == {
        t_n_ref,
        t_p_ref,
        o_n_ref,
        o_p_ref,
    }

    # close references
    p_ref.connect(other_usb.p.reference)

    connected_per_mif_post = {ref: ref.get_connected(include_self=True) for ref in refs}
    for _, connected in connected_per_mif_post.items():
        assert set(connected.keys()).issuperset(refs)


def test_regression_rp2040_usb_diffpair():
    app = RP2040_ReferenceDesign()

    terminated_usb = cast_assert(F.USB2_0_IF.Data, app.runtime["_terminated_usb_data"])
    rp_usb = app.rp2040.usb

    t_p_ref = terminated_usb.p.reference
    t_n_ref = terminated_usb.n.reference
    r_p_ref = rp_usb.p.reference
    r_n_ref = rp_usb.n.reference
    refs = [
        r_p_ref,
        r_n_ref,
        t_p_ref,
        t_n_ref,
    ]

    connected_per_mif = {ref: ref.get_connected(include_self=True) for ref in refs}
    for connected in connected_per_mif.values():
        assert set(connected.keys()) == set(refs)


@pytest.mark.slow
def test_regression_rp2040_usb_diffpair_full():
    app = RP2040_ReferenceDesign()
    rp2040_2 = RP2040()
    rp2040_3 = RP2040()

    # make graph bigger
    app.rp2040.i2c[0].connect(rp2040_2.i2c[0])
    app.rp2040.i2c[0].connect(rp2040_3.i2c[0])

    F.is_bus_parameter.resolve_bus_parameters(app.get_graph())


def test_connect_incompatible():
    class A(ModuleInterface):
        pass

    class B(ModuleInterface):
        pass

    x = A()
    y = B()
    with pytest.raises(NodeException):
        x.connect(y)  # type: ignore


def test_connect_incompatible_hierarchical():
    class A(ModuleInterface):
        pass

    class B(A):
        pass

    x = A()
    y = B()
    with pytest.raises(NodeException):
        x.connect(y)  # type: ignore


def test_connect_incompatible_hierarchical_regression():
    x = F.ElectricPower()
    y = F.Electrical()

    with pytest.raises(NodeException):
        x.connect(y)  # type: ignore
