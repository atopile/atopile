# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from itertools import chain, pairwise

import pytest

import faebryk.core.node as fabll
import faebryk.library._F as F

# from faebryk.core.link import (
#     LinkDirect,
#     LinkDirectConditional,
#     LinkDirectConditionalFilterResult,
#     LinkDirectDerived,
# )
from faebryk.core.node import IMPLIED_PATHS
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import GraphView

# from faebryk.libs.app.erc import (
#     ERCFaultShortedModuleInterfaces,
#     ERCPowerSourcesShortedError,
#     simple_erc,
# )
from faebryk.libs.util import cast_assert, times

# from test.common.resources.fabll_modules.ButtonCell import ButtonCell
# from test.common.resources.fabll_modules.RP2040 import RP2040
# from test.common.resources.fabll_modules.RP2040_ReferenceDesign import (
#     RP2040_ReferenceDesign,
# )

logger = logging.getLogger(__name__)


def ensure_typegraph(node: fabll.Node) -> fabll.Node:
    """Build TypeGraph, instantiate, and bind for the node's tree."""
    root = node._get_root()

    # Assert not already built
    assert not root.get_lifecycle_stage() == "runtime", "TypeGraph already built"
    assert not getattr(root, "_instance_bound", None), "Instance already bound"

    # Instantiate graph and execute runtime hooks
    fabll.Node.instantiate(root)
    return root


def bind_to_module(*nodes: fabll.Node) -> fabll.Module:
    class _Harness(fabll.Node):
        pass

    harness = _Harness()
    for idx, node in enumerate(nodes):
        harness.add(node, name=f"node_{idx}")
    return harness


def test_self():
    g = GraphView.create()
    mif = fabll.ModuleInterface._create_instance(TypeGraph.create(g=g), g)
    assert mif.get_trait(fabll.is_interface).is_connected_to(mif)

@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
def test_up_connect_simple_single():
    """
    ```
    H1      H2
     L1 -->  L1
    ```
    """

    class High(fabll.Node):
        lower: fabll.ModuleInterface

    high1 = High()
    high2 = High()

    high1.lower.connect(high2.lower)
    assert high1.is_connected_to(high2)

@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
def test_up_connect_simple_two():
    """
    ```
    H1      H2
     L1 -->  L1
     L2 -->  L2
    ```
    """

    class High(fabll.Node):
        lower1: fabll.ModuleInterface
        lower2: fabll.ModuleInterface

    high1 = High()
    high2 = High()

    high1.lower1.connect(high2.lower1)
    high1.lower2.connect(high2.lower2)
    assert high1.is_connected_to(high2)

@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
def test_up_connect_simple_multiple():
    """
    ```
    H1      H2
     L1 -->  L1
     L2 -->  L2
     L3 -->  L3
    ```
    """

    class High(fabll.Node):
        lower1: fabll.ModuleInterface
        lower2: fabll.ModuleInterface
        lower3: fabll.ModuleInterface

    high1 = High()
    high2 = High()

    high1.lower1.connect(high2.lower1)
    high1.lower2.connect(high2.lower2)
    high1.lower3.connect(high2.lower3)
    assert high1.is_connected_to(high2)

@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
def test_up_connect_chain_simple():
    """
    ```
    H1            H2
     L1 --> M -->  L1
     L2 -------->  L2
    ```
    """

    class High(fabll.Node):
        lower1: fabll.ModuleInterface
        lower2: fabll.ModuleInterface

    high1 = High()
    high2 = High()

    middle = fabll.ModuleInterface()

    high1.lower1.connect(middle)
    high2.lower1.connect(middle)
    high1.lower2.connect(high2.lower2)

    assert high1.is_connected_to(high2)


@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
def test_up_connect_chain_multiple_same():
    """
    ```
    H1      H2      H3
     L1 -->  L1 -->  L1
     L2 -->  L2 -->  L2
    ```
    """

    class High(fabll.Node):
        lower1: fabll.ModuleInterface
        lower2: fabll.ModuleInterface

    high1 = High()
    high2 = High()
    high3 = High()

    high1.lower1.connect(high2.lower1)
    high1.lower2.connect(high2.lower2)
    high2.lower1.connect(high3.lower1)
    high2.lower2.connect(high3.lower2)

    assert high1.is_connected_to(high3)


@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
def test_up_connect_chain_multiple_mixed():
    """
    ```
    H1      H2  ==>  H3      H4
     L1 -->  L1       L1 -->  L1
     L2 -->  L2       L2 -->  L2
    ```
    """

    class Low(fabll.Node): ...

    class High(fabll.Node):
        lower1: Low
        lower2: Low

    high1, high2, high3, high4 = times(4, High)

    high1.lower1.connect(high2.lower1)
    high1.lower2.connect(high2.lower2)
    high2.connect_shallow(high3)
    high3.lower1.connect(high4.lower1)
    high3.lower2.connect(high4.lower2)

    assert high1.is_connected_to(high4)


@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
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

    class Low(fabll.Node): ...

    class High(fabll.Node):
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

    class Low(fabll.Node): ...

    class High(fabll.Node):
        lower1: Low
        lower2: Low

    class App(fabll.Node):
        high = fabll.list_field(4, High)

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


@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
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

    class Low(fabll.Node): ...

    class High(fabll.Node):
        lower1: Low
        lower2: Low

    class App(fabll.Node):
        high = fabll.list_field(4, High)

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

    class Low(fabll.Node): ...

    class High(fabll.Node):
        lower1: Low
        lower2: Low

    class Higher(fabll.Node):
        high: High

    class App(fabll.Node):
        high = fabll.list_field(3, High)
        higher = fabll.list_field(2, Higher)

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


@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
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

    class Low(fabll.Node): ...

    class High(fabll.Node):
        lower1: Low
        lower2: Low

    class App(fabll.Node):
        high = fabll.list_field(4, High)

    app = App()

    high1, high2, high3, high4 = app.high

    high1.lower1.connect(high2.lower2)
    high1.lower2.connect(high2.lower1)
    high2.connect_shallow(high3)
    high3.lower1.connect(high4.lower2)
    high3.lower2.connect(high4.lower1)

    assert high1.is_connected_to(high4)


@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
def test_split_flip_negative():
    """
    Miro: Implied Bus Non-Connection
    ```
    H1     H2
     L1 --> L2
     L2 --> L1
    ```
    """

    class Low(fabll.Node): ...

    class High(fabll.Node):
        lower1: Low
        lower2: Low

    high1, high2 = times(2, High)

    high1.lower1.connect(high2.lower2)
    high1.lower2.connect(high2.lower1)

    assert not high1.is_connected_to(high2)


@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
def test_up_connect_chain_multiple_mixed_simulate_realworld():
    """
    ```
    H1      H2  ==>  H3      H4
     L1 -->  L1       L1 -->  L1
     L2 ---  L2 ----- L2 ---  L2
    ```
    """

    class Low(fabll.Node): ...

    class High(fabll.Node):
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


@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
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

    class Low(fabll.Node): ...

    class High(fabll.Node):
        lower1: Low
        lower2: Low

    class Higher(fabll.Node):
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


@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
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

    class High(fabll.Node):
        lower1: fabll.ModuleInterface
        lower2: fabll.ModuleInterface

    class Higher(fabll.Node):
        high1: High
        high2: High

    higher1 = Higher()
    higher2 = Higher()

    higher1.high1.lower1.connect(higher2.high1.lower1)
    higher1.high1.lower2.connect(higher2.high1.lower2)
    higher1.high2.lower1.connect(higher2.high2.lower1)
    higher1.high2.lower2.connect(higher2.high2.lower2)
    assert higher1.is_connected_to(higher2)

@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
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

    class Low(fabll.Node): ...

    class High(fabll.Node):
        lower1: Low
        lower2: Low

    class Higher(fabll.Node):
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
    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    class High(fabll.Node):
        _is_interface = fabll.is_interface.MakeChild()
        lower1 = fabll.ModuleInterface.MakeChild()
        lower2 = fabll.ModuleInterface.MakeChild()

    highType = High.bind_typegraph(tg)
    high1 = highType.create_instance(g=g)
    high2 = highType.create_instance(g=g)

    high1.lower1.get().get_trait(fabll.is_interface).connect_to(high2.lower1.get())
    assert not high1.get_trait(fabll.is_interface).is_connected_to(high2)


def test_up_connect_simple_multiple_negative():
    """
    ```
    H1      H2
     L1 -->  L1
     L2 -->  L2
     L3      L3
    ```
    """

    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    class High(fabll.Node):
        _is_interface = fabll.is_interface.MakeChild()
        lower1 = fabll.ModuleInterface.MakeChild()
        lower2 = fabll.ModuleInterface.MakeChild()
        lower3 = fabll.ModuleInterface.MakeChild()

    highType = High.bind_typegraph(tg)
    high1 = highType.create_instance(g=g)
    high2 = highType.create_instance(g=g)

    high1.lower1.get().get_trait(fabll.is_interface).connect_to(high2.lower1.get())
    high1.lower2.get().get_trait(fabll.is_interface).connect_to(high2.lower2.get())
    assert not high1.get_trait(fabll.is_interface).is_connected_to(high2)


@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
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

    class UARTBuffer(fabll.Node):
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

    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    electricPowerType = F.ElectricPower.bind_typegraph(tg)
    ep = [electricPowerType.create_instance(g=g) for _ in range(2)]

    ep[0].get_trait(fabll.is_interface).connect_to(ep[1])

    assert ep[0].get_trait(fabll.is_interface).is_connected_to(ep[1])
    assert ep[0].hv.get().get_trait(fabll.is_interface).is_connected_to(ep[1].hv.get())
    assert ep[0].lv.get().get_trait(fabll.is_interface).is_connected_to(ep[1].lv.get())


def test_chains_direct():
    """
    ```
    M1 --> M2 --> M3
    ```
    """
    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    electricalType = F.Electrical.bind_typegraph(tg)
    electrics = [electricalType.create_instance(g=g) for _ in range(3)]

    electrics[0].get_trait(fabll.is_interface).connect_to(electrics[1])
    electrics[1].get_trait(fabll.is_interface).connect_to(electrics[2])
    assert electrics[0].get_trait(fabll.is_interface).is_connected_to(electrics[2])


def test_chains_double_shallow_flat():
    """
    ```
    M1 ==> M2 ==> M3
    ```
    """

    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    electricalType = F.Electrical.bind_typegraph(tg)
    electrics = [electricalType.create_instance(g=g) for _ in range(3)]

    electrics[0].get_trait(fabll.is_interface).connect_shallow_to(electrics[1])
    electrics[1].get_trait(fabll.is_interface).connect_shallow_to(electrics[2])
    assert electrics[0].get_trait(fabll.is_interface).is_connected_to(electrics[2])


def test_chains_mixed_shallow_flat():
    """
    ```
    M1 ==> M2 --> M3
    ```
    """

    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    electricalType = F.Electrical.bind_typegraph(tg)
    electrics = [electricalType.create_instance(g=g) for _ in range(3)]

    electrics[0].get_trait(fabll.is_interface).connect_shallow_to(electrics[1])
    electrics[1].get_trait(fabll.is_interface).connect_to(electrics[2])
    assert electrics[0].get_trait(fabll.is_interface).is_connected_to(electrics[2])


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
    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    electricalLogicType = F.ElectricLogic.bind_typegraph(tg)
    el = [electricalLogicType.create_instance(g=g) for _ in range(3)]

    el[0].get_trait(fabll.is_interface).connect_shallow_to(el[1])
    el[1].get_trait(fabll.is_interface).connect_to(el[2])

    assert el[0].get_trait(fabll.is_interface).is_connected_to(el[2])

    assert el[1].line.get().get_trait(fabll.is_interface).is_connected_to(el[2].line.get())
    assert el[1].reference.get().get_trait(fabll.is_interface).is_connected_to(el[2].reference.get())
    assert not el[0].line.get().get_trait(fabll.is_interface).is_connected_to(el[1].line.get())
    assert not el[0].reference.get().get_trait(fabll.is_interface).is_connected_to(el[1].reference.get())
    assert not el[0].line.get().get_trait(fabll.is_interface).is_connected_to(el[2].line.get())
    assert not el[0].reference.get().get_trait(fabll.is_interface).is_connected_to(el[2].reference.get())

    # Test duplicate resolution
    el[0].line.get().get_trait(fabll.is_interface).connect_to(el[1].line.get())
    el[0].reference.get().get_trait(fabll.is_interface).connect_to(el[1].reference.get())
    assert el[0].get_trait(fabll.is_interface).is_connected_to(el[1])
    assert el[0].get_trait(fabll.is_interface).is_connected_to(el[2])


def test_loooooong_chain():
    """Let's make it hard"""
    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    electricPowerType = F.ElectricPower.bind_typegraph(tg)
    ep = [electricPowerType.create_instance(g=g) for _ in range(2**10)]

    for left, right in pairwise(ep):
        left.get_trait(fabll.is_interface).connect_to(right)

    assert ep[0].get_trait(fabll.is_interface).is_connected_to(ep[-1])


# FIXME: this should be WAYYY higher than 16
@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
@pytest.mark.parametrize("length", [16])
def test_alternating_long_chain(length):
    """Let's make it hard"""
    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    electricPowerType = F.ElectricPower.bind_typegraph(tg)
    ep = [electricPowerType.create_instance(g=g) for _ in range(length)]

    for i, (left, right) in enumerate(pairwise(ep)):
        if i % 2:
            left.get_trait(fabll.is_interface).connect_to(right)
        else:
            left.lv.get().get_trait(fabll.is_interface).connect_to(right.lv.get())
            left.hv.get().get_trait(fabll.is_interface).connect_to(right.hv.get())

    assert ep[0].get_trait(fabll.is_interface).is_connected_to(ep[-1])
    assert ep[0].lv.get().get_trait(fabll.is_interface).is_connected_to(ep[-1].lv.get())
    assert ep[0].hv.get().get_trait(fabll.is_interface).is_connected_to(ep[-1].hv.get())

@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
def test_shallow_bridge_simple():
    """
    ```
                B
    H1      HI ===> HO     H2
     L1 -->  L1      L1 --> L1
     L2 -->  L2      L2 --> L2
    ```
    """

    class Low(fabll.Node): ...

    class High(fabll.Node):
        lower1: Low
        lower2: Low

    class ShallowBridge(fabll.Node):
        high_in: High
        high_out: High

        def __preinit__(self) -> None:
            self.high_in.connect_shallow(self.high_out)

        @fabll.rt_field
        def can_bridge(self):
            return F.can_bridge(self.high_in, self.high_out)

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

    class Buffer(fabll.Node):
        ins: F.Electrical
        outs: F.Electrical

        ins_l: F.ElectricLogic
        outs_l: F.ElectricLogic

        def __preinit__(self) -> None:
            self.ins_l.signal.connect(self.ins)
            self.outs_l.signal.connect(self.outs)

            self.ins_l.connect_shallow(self.outs_l)

        @fabll.rt_field
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

    class Buffer(fabll.Node):
        ins = fabll.list_field(2, F.Electrical)
        outs = fabll.list_field(2, F.Electrical)

        ins_l = fabll.list_field(2, F.ElectricLogic)
        outs_l = fabll.list_field(2, F.ElectricLogic)

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

        @fabll.rt_field
        def single_electric_reference(self):
            return F.has_single_electric_reference_defined(
                F.ElectricLogic.connect_all_module_references(self)
            )

    class UARTBuffer(fabll.Node):
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

        @fabll.rt_field
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


class Specialized(fabll.Node): ...


# class DoubleSpecialized(Specialized): ...

@pytest.mark.xfail(reason="No specialized links yet")
def test_specialize_general_to_special():
    # general connection -> specialized connection
    mifs = times(3, fabll.ModuleInterface)
    mifs_special = times(3, Specialized)

    mifs[0].connect(mifs[1])
    mifs[1].connect(mifs[2])

    mifs[0].specialize(mifs_special[0])
    mifs[2].specialize(mifs_special[2])

    assert mifs_special[0].is_connected_to(mifs_special[2])

@pytest.mark.xfail(reason="No specialized links yet")
def test_specialize_special_to_general():
    # specialized connection -> general connection
    mifs = times(3, fabll.ModuleInterface)
    mifs_special = times(3, Specialized)

    mifs_special[0].connect(mifs_special[1])
    mifs_special[1].connect(mifs_special[2])

    mifs[0].specialize(mifs_special[0])
    mifs[2].specialize(mifs_special[2])

    assert mifs[0].is_connected_to(mifs[2])


@pytest.mark.xfail(reason="No specialized links yet")
def test_specialize_link():
    # test special link
    class _Link(LinkDirectConditional):
        def __init__(self):
            super().__init__(
                lambda path: LinkDirectConditionalFilterResult.FILTER_PASS,
                needs_only_first_in_path=True,
            )

    mifs = times(3, fabll.ModuleInterface)
    mifs_special = times(3, Specialized)

    mifs[0].connect(mifs[1], link=_Link)
    mifs[1].connect(mifs[2])

    recorded_0 = mifs[0]._get_recorded_link_types()
    assert recorded_0[mifs[1]] == {_Link}
    recorded_1 = mifs[1]._get_recorded_link_types()
    assert recorded_1[mifs[0]] == {_Link}
    assert mifs[1]._get_recorded_link_types().get(mifs[2]) is None

    mifs[0].specialize(mifs_special[0])
    mifs[2].specialize(mifs_special[2])

    assert mifs_special[0].is_connected_to(mifs_special[2])

@pytest.mark.xfail(reason="No specialized links yet")
def test_specialize_double_with_gap():
    # double specialization with gap
    mifs = times(2, fabll.ModuleInterface)
    mifs_special = times(1, Specialized)
    mifs_double_special = times(2, DoubleSpecialized)

    mifs[0].connect(mifs[1])
    mifs[0].specialize(mifs_special[0])
    mifs_special[0].specialize(mifs_double_special[0])
    mifs[1].specialize(mifs_double_special[1])

    assert mifs_double_special[0].is_connected_to(mifs_double_special[1])

@pytest.mark.xfail(reason="No specialized links yet")
def test_specialize_double_with_gap_2():
    mifs = times(2, fabll.ModuleInterface)
    mifs_special = times(1, Specialized)
    mifs_double_special = times(2, DoubleSpecialized)

    mifs_double_special[0].connect(mifs_double_special[1])
    mifs[0].specialize(mifs_special[0])
    mifs_special[0].specialize(mifs_double_special[0])
    mifs[1].specialize(mifs_double_special[1])

    assert mifs[0].is_connected_to(mifs[1])

@pytest.mark.xfail(reason="No specialized links yet")
def test_specialize_module():
    battery = F.Battery()
    power = F.ElectricPower()

    battery.power.connect(power)
    buttoncell = battery.specialize(ButtonCell())

    assert buttoncell.power.is_connected_to(battery.power)
    assert power.is_connected_to(buttoncell.power)

@pytest.mark.xfail(reason="No conditional links yet")
def test_isolated_connect_simple():
    x1 = F.ElectricLogic()
    x2 = F.ElectricLogic()
    x1.connect(x2, link=F.ElectricLogic.LinkIsolatedReference)

    assert x1.is_connected_to(x2)
    assert x1.line.is_connected_to(x2.line)

    assert not x1.reference.is_connected_to(x2.reference)
    assert not x1.reference.hv.is_connected_to(x2.reference.hv)


def test_basic_i2c():
    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    I2CType = F.I2C.bind_typegraph(tg)
    i2c1 = I2CType.create_instance(g=g)
    i2c2 = I2CType.create_instance(g=g)

    i2c1.get_trait(fabll.is_interface).connect_to(i2c2)

    # I2C's connected
    assert i2c1.get_trait(fabll.is_interface).is_connected_to(i2c2)

    # Electric signals connected
    assert i2c1.scl.get().get_trait(fabll.is_interface).is_connected_to(i2c2.scl.get())
    assert i2c1.sda.get().get_trait(fabll.is_interface).is_connected_to(i2c2.sda.get())

    assert ~i2c1.scl.get().get_trait(fabll.is_interface).is_connected_to(i2c2.sda.get())

    # Electricals connected
    assert (
        i2c1.scl.get()
        .line.get()
        .get_trait(fabll.is_interface)
        .is_connected_to(i2c2.scl.get().line.get())
    )
    assert (
        i2c1.sda.get()
        .line.get()
        .get_trait(fabll.is_interface)
        .is_connected_to(i2c2.sda.get().line.get())
    )

    # Electric powers connected
    assert (
        i2c1.scl.get()
        .reference.get()
        .get_trait(fabll.is_interface)
        .is_connected_to(i2c2.scl.get().reference.get())
    )
    assert (
        i2c1.sda.get()
        .reference.get()
        .get_trait(fabll.is_interface)
        .is_connected_to(i2c2.sda.get().reference.get())
    )

    # Electric powers electricals connected
    assert (
        i2c1.scl.get()
        .reference.get()
        .hv.get()
        .get_trait(fabll.is_interface)
        .is_connected_to(i2c2.scl.get().reference.get().hv.get())
    )
    assert (
        i2c1.scl.get()
        .reference.get()
        .lv.get()
        .get_trait(fabll.is_interface)
        .is_connected_to(i2c2.scl.get().reference.get().lv.get())
    )
    assert (
        i2c1.sda.get()
        .reference.get()
        .hv.get()
        .get_trait(fabll.is_interface)
        .is_connected_to(i2c2.sda.get().reference.get().hv.get())
    )
    assert (
        i2c1.sda.get()
        .reference.get()
        .lv.get()
        .get_trait(fabll.is_interface)
        .is_connected_to(i2c2.sda.get().reference.get().lv.get())
    )

    assert ~i2c1.scl.get().reference.get().hv.get().get_trait(
        fabll.is_interface
    ).is_connected_to(i2c2.scl.get().reference.get().lv.get())
    assert ~i2c1.scl.get().reference.get().lv.get().get_trait(
        fabll.is_interface
    ).is_connected_to(i2c2.scl.get().reference.get().hv.get())
    assert ~i2c1.sda.get().reference.get().hv.get().get_trait(
        fabll.is_interface
    ).is_connected_to(i2c2.sda.get().reference.get().lv.get())
    assert ~i2c1.sda.get().reference.get().lv.get().get_trait(
        fabll.is_interface
    ).is_connected_to(i2c2.sda.get().reference.get().hv.get())


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

    harness = bind_to_module(*powers)

    # direct implied
    powers[0].connect(powers[1])
    ensure_typegraph(harness)

    assert powers[1].hv in powers[0].hv.get_connected()

    paths = powers[0].hv.is_connected_to(powers[1].hv)
    assert paths
    path = paths[0]
    assert len(path) == 4
    assert isinstance(path[1].is_connected_to(path[2]), LinkDirectDerived)


@pytest.mark.skipif(not IMPLIED_PATHS, reason="IMPLIED_PATHS is not set")
def test_children_implied_paths():
    powers = times(3, F.ElectricPower)

    harness = bind_to_module(*powers)

    # children implied
    powers[0].connect(powers[1])
    powers[1].hv.connect(powers[2].hv)
    powers[1].lv.connect(powers[2].lv)
    ensure_typegraph(harness)

    assert powers[2] in powers[0].get_connected()

    paths = list(powers[0].is_connected_to(powers[2]))
    assert paths
    assert len(paths[0]) == 4
    assert isinstance(paths[0][1].is_connected_to(paths[0][2]), LinkDirectDerived)


@pytest.mark.skipif(not IMPLIED_PATHS, reason="IMPLIED_PATHS is not set")
def test_shallow_implied_paths():
    powers = times(4, F.ElectricPower)

    harness = bind_to_module(*powers)

    # shallow implied
    powers[0].connect(powers[1])
    powers[1].hv.connect(powers[2].hv)
    powers[1].lv.connect(powers[2].lv)
    powers[2].connect_shallow(powers[3])
    ensure_typegraph(harness)

    assert powers[3] in powers[0].get_connected()

    assert not powers[0].hv.is_connected_to(powers[3].hv)


def test_direct_shallow_instance():
    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    electricalType = F.Electrical.bind_typegraph(tg)
    electrical1 = electricalType.create_instance(g=g)
    electrical2 = electricalType.create_instance(g=g)
    electrical3 = electricalType.create_instance(g=g)

    electrical1.get_trait(fabll.is_interface).connect_shallow_to(electrical2)
    electrical1.get_trait(fabll.is_interface).connect_shallow_to(electrical3)
    assert electrical1.get_trait(fabll.is_interface).is_connected_to(electrical2)
    assert electrical1.get_trait(fabll.is_interface).is_connected_to(electrical3)


def test_connect_incompatible():
    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    class A(fabll.Node):
        _is_interface = fabll.is_interface.MakeChild()
    class B(fabll.Node):
        _is_interface = fabll.is_interface.MakeChild()

    aType = A.bind_typegraph(tg)
    bType = B.bind_typegraph(tg)
    a = aType.create_instance(g=g)
    b = bType.create_instance(g=g)

    with pytest.raises(ValueError, match="Failed to connect"):
        a.get_trait(fabll.is_interface).connect_to(b)


def test_connect_incompatible_hierarchical():
    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    class B(fabll.Node):
        _is_interface = fabll.is_interface.MakeChild()

    class A(fabll.Node):
        _is_interface = fabll.is_interface.MakeChild()
        b = B.MakeChild()

    aType = A.bind_typegraph(tg)
    bType = B.bind_typegraph(tg)
    x = aType.create_instance(g=g)
    y = bType.create_instance(g=g)
    with pytest.raises(ValueError, match="Failed to connect"):
        x.get_trait(fabll.is_interface).connect_to(y)


def test_connect_incompatible_hierarchical_regression():
    g = GraphView.create()
    tg = TypeGraph.create(g=g)

    electricPowerType = F.ElectricPower.bind_typegraph(tg)
    electricalType = F.Electrical.bind_typegraph(tg)
    x = electricPowerType.create_instance(g=g)
    y = electricalType.create_instance(g=g)

    with pytest.raises(ValueError, match="Failed to connect"):
        x.get_trait(fabll.is_interface).connect_to(y)
