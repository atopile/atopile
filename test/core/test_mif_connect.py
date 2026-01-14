# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from itertools import chain, pairwise

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.node import IMPLIED_PATHS
from faebryk.libs.util import times

logger = logging.getLogger(__name__)


def ensure_typegraph(node: fabll.Node) -> fabll.Node:
    """Build fbrk.GraphView, instantiate, and bind for the node's tree."""
    root = node._get_root()

    # Assert not already built
    assert not root.get_lifecycle_stage() == "runtime", "fbrk.GraphView already built"
    assert not getattr(root, "_instance_bound", None), "Instance already bound"

    # Instantiate graph and execute runtime hooks
    fabll.Node.instantiate(root)
    return root


def bind_to_module(*nodes: fabll.Node) -> fabll.Module:
    class _Harness(fabll.Node):
        pass

    harness = _Harness()
    for idx, node in enumerate(nodes):
        harness.add_child(node, identifier=f"node_{idx}")
    return harness


def test_self():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    elec = F.Electrical.bind_typegraph(tg).create_instance(g=g)
    assert elec._is_interface.get().is_connected_to(elec)


@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
def test_up_connect_simple_single():
    """
    ```
    H1      H2
     L1 -->  L1
    ```
    """
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _Lower(fabll.Node):
        is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    class _High(fabll.Node):
        is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
        lower = _Lower.MakeChild()

    high = _High.bind_typegraph(tg)
    high1 = high.create_instance(g=g)
    high2 = high.create_instance(g=g)

    high1.lower.get().is_interface.get().connect_to(high2.lower.get())
    assert high1.is_interface.get().is_connected_to(high2)


@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
def test_up_connect_simple_two():
    """
    ```
    H1      H2
     L1 -->  L1
     L2 -->  L2
    ```
    """

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _Lower(fabll.Node):
        is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    class _High(fabll.Node):
        is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
        lower1 = _Lower.MakeChild()
        lower2 = _Lower.MakeChild()

    high = _High.bind_typegraph(tg)
    high1 = high.create_instance(g=g)
    high2 = high.create_instance(g=g)

    high1.lower1.get().is_interface.get().connect_to(high2.lower1.get())
    high1.lower2.get().is_interface.get().connect_to(high2.lower2.get())
    assert high1.is_interface.get().is_connected_to(high2)


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
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _Lower(fabll.Node):
        is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    class _High(fabll.Node):
        is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
        lower1 = _Lower.MakeChild()
        lower2 = _Lower.MakeChild()
        lower3 = _Lower.MakeChild()

    high = _High.bind_typegraph(tg)
    high1 = high.create_instance(g=g)
    high2 = high.create_instance(g=g)
    high1.lower1.get().is_interface.get().connect_to(high2.lower1.get())
    high1.lower2.get().is_interface.get().connect_to(high2.lower2.get())
    high1.lower3.get().is_interface.get().connect_to(high2.lower3.get())
    assert high1.is_interface.get().is_connected_to(high2)


@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
def test_up_connect_chain_simple():
    """
    ```
    H1            H2
     L1 --> M -->  L1
     L2 -------->  L2
    ```
    """

    class _High(fabll.Node):
        lower1: fabll.ModuleInterface
        lower2: fabll.ModuleInterface

    high1 = _High()
    high2 = _High()

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

    class _High(fabll.Node):
        lower1: fabll.ModuleInterface
        lower2: fabll.ModuleInterface

    high1 = _High()
    high2 = _High()
    high3 = _High()

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

    class _Low(fabll.Node): ...

    class _High(fabll.Node):
        lower1: _Low
        lower2: _Low

    high1, high2, high3, high4 = times(4, _High)

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

    class _Low(fabll.Node): ...

    class _High(fabll.Node):
        lower1: _Low
        lower2: _Low

    high1, high2, high3 = times(3, _High)

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

    class _Low(fabll.Node): ...

    class _High(fabll.Node):
        lower1: _Low
        lower2: _Low

    class _App(fabll.Node):
        high = [_High.MakeChild() for _ in range(4)]

    app = _App()

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

    class _Low(fabll.Node): ...

    class _High(fabll.Node):
        lower1: _Low
        lower2: _Low

    class _App(fabll.Node):
        high = [_High.MakeChild() for _ in range(4)]

    app = _App()

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

    class _Low(fabll.Node): ...

    class _High(fabll.Node):
        lower1: _Low
        lower2: _Low

    class _Higher(fabll.Node):
        high: _High

    class _App(fabll.Node):
        high = [_High.MakeChild() for _ in range(3)]
        higher = [_Higher.MakeChild() for _ in range(2)]

    app = _App()

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

    class _Low(fabll.Node): ...

    class _High(fabll.Node):
        lower1: _Low
        lower2: _Low

    class _App(fabll.Node):
        high = [_High.MakeChild() for _ in range(4)]

    app = _App()

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

    class _Low(fabll.Node): ...

    class _High(fabll.Node):
        lower1: _Low
        lower2: _Low

    high1, high2 = times(2, _High)

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

    class _Low(fabll.Node): ...

    class _High(fabll.Node):
        lower1: _Low
        lower2: _Low

    high1, high2, high3, high4 = times(4, _High)

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

    class _Low(fabll.Node): ...

    class _High(fabll.Node):
        lower1: _Low
        lower2: _Low

    class _Higher(fabll.Node):
        high1: _High
        high2: _High

    higher_begin = _Higher()
    higher_end = _Higher()

    high_middle1 = _High()
    high_middle2 = _High()

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

    class _High(fabll.Node):
        lower1: fabll.ModuleInterface
        lower2: fabll.ModuleInterface

    class _Higher(fabll.Node):
        high1: _High
        high2: _High

    higher1 = _Higher()
    higher2 = _Higher()

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

    class _Low(fabll.Node): ...

    class _High(fabll.Node):
        lower1: _Low
        lower2: _Low

    class _Higher(fabll.Node):
        high1: _High
        high2: _High

    higher1 = _Higher()
    higher2 = _Higher()

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
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _High(fabll.Node):
        _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
        lower1 = F.Electrical.MakeChild()
        lower2 = F.Electrical.MakeChild()

    highType = _High.bind_typegraph(tg)
    high1 = highType.create_instance(g=g)
    high2 = highType.create_instance(g=g)

    high1.lower1.get()._is_interface.get().connect_to(high2.lower1.get())
    assert not high1._is_interface.get().is_connected_to(high2)


def test_up_connect_simple_multiple_negative():
    """
    ```
    H1      H2
     L1 -->  L1
     L2 -->  L2
     L3      L3
    ```
    """

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _High(fabll.Node):
        _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
        lower1 = F.Electrical.MakeChild()
        lower2 = F.Electrical.MakeChild()
        lower3 = F.Electrical.MakeChild()

    highType = _High.bind_typegraph(tg)
    high1 = highType.create_instance(g=g)
    high2 = highType.create_instance(g=g)

    high1.lower1.get()._is_interface.get().connect_to(high2.lower1.get())
    high1.lower2.get()._is_interface.get().connect_to(high2.lower2.get())
    assert not high1._is_interface.get().is_connected_to(high2)


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

    class _UARTBuffer(fabll.Node):
        bus_in: F.UART_Base
        bus_out: F.UART_Base

        def __preinit__(self) -> None:
            self.bus_in.rx.line.connect(self.bus_out.rx.line)
            self.bus_in.tx.line.connect(self.bus_out.tx.line)
            self.bus_in.rx.reference.connect(self.bus_out.rx.reference)

    app = _UARTBuffer()

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

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    electricPowerType = F.ElectricPower.bind_typegraph(tg)
    ep = [electricPowerType.create_instance(g=g) for _ in range(2)]

    ep[0]._is_interface.get().connect_to(ep[1])

    assert ep[0]._is_interface.get().is_connected_to(ep[1])
    assert ep[0].hv.get()._is_interface.get().is_connected_to(ep[1].hv.get())
    assert ep[0].lv.get()._is_interface.get().is_connected_to(ep[1].lv.get())


def test_chains_direct():
    """
    ```
    M1 --> M2 --> M3
    ```
    """
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    electricalType = F.Electrical.bind_typegraph(tg)
    electrics = [electricalType.create_instance(g=g) for _ in range(3)]

    electrics[0]._is_interface.get().connect_to(electrics[1])
    electrics[1]._is_interface.get().connect_to(electrics[2])
    assert electrics[0]._is_interface.get().is_connected_to(electrics[2])


def test_chains_double_shallow_flat():
    """
    ```
    M1 ==> M2 ==> M3
    ```
    """

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    electricalType = F.Electrical.bind_typegraph(tg)
    electrics = [electricalType.create_instance(g=g) for _ in range(3)]

    electrics[0]._is_interface.get().connect_shallow_to(electrics[1])
    electrics[1]._is_interface.get().connect_shallow_to(electrics[2])
    assert electrics[0]._is_interface.get().is_connected_to(electrics[2])


def test_chains_mixed_shallow_flat():
    """
    ```
    M1 ==> M2 --> M3
    ```
    """

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    electricalType = F.Electrical.bind_typegraph(tg)
    electrics = [electricalType.create_instance(g=g) for _ in range(3)]

    electrics[0]._is_interface.get().connect_shallow_to(electrics[1])
    electrics[1]._is_interface.get().connect_to(electrics[2])
    assert electrics[0]._is_interface.get().is_connected_to(electrics[2])


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
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    electricalLogicType = F.ElectricLogic.bind_typegraph(tg)
    el = [electricalLogicType.create_instance(g=g) for _ in range(3)]

    el[0]._is_interface.get().connect_shallow_to(el[1])
    el[1]._is_interface.get().connect_to(el[2])

    assert el[0]._is_interface.get().is_connected_to(el[2])

    assert el[1].line.get()._is_interface.get().is_connected_to(el[2].line.get())
    assert (
        el[1].reference.get()._is_interface.get().is_connected_to(el[2].reference.get())
    )
    assert not el[0].line.get()._is_interface.get().is_connected_to(el[1].line.get())
    assert (
        not el[0]
        .reference.get()
        ._is_interface.get()
        .is_connected_to(el[1].reference.get())
    )
    assert not el[0].line.get()._is_interface.get().is_connected_to(el[2].line.get())
    assert (
        not el[0]
        .reference.get()
        ._is_interface.get()
        .is_connected_to(el[2].reference.get())
    )

    # Test duplicate resolution
    el[0].line.get()._is_interface.get().connect_to(el[1].line.get())
    el[0].reference.get()._is_interface.get().connect_to(el[1].reference.get())
    assert el[0]._is_interface.get().is_connected_to(el[1])
    assert el[0]._is_interface.get().is_connected_to(el[2])


def test_shallow_blocks_child_parent_child():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    electricalLogicType = F.ElectricLogic.bind_typegraph(tg)
    el1 = electricalLogicType.create_instance(g=g)
    el2 = electricalLogicType.create_instance(g=g)

    # Shallow at parent level should not allow child->parent->shallow->child
    el1._is_interface.get().connect_shallow_to(el2)

    assert el1._is_interface.get().is_connected_to(el2)
    assert not el1.line.get()._is_interface.get().is_connected_to(el2.line.get())
    assert (
        not el1.reference.get()._is_interface.get().is_connected_to(el2.reference.get())
    )

    # Full connect should propagate to children
    el1._is_interface.get().connect_to(el2)
    assert el1.line.get()._is_interface.get().is_connected_to(el2.line.get())
    assert el1.reference.get()._is_interface.get().is_connected_to(el2.reference.get())


def test_loooooong_chain():
    """Let's make it hard"""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    electricPowerType = F.ElectricPower.bind_typegraph(tg)
    ep = [electricPowerType.create_instance(g=g) for _ in range(2**10)]

    for left, right in pairwise(ep):
        left._is_interface.get().connect_to(right)

    assert ep[0]._is_interface.get().is_connected_to(ep[-1])


# FIXME: this should be WAYYY higher than 16
@pytest.mark.xfail(reason="Split-paths/up-connects not supported yet")
@pytest.mark.parametrize("length", [16])
def test_alternating_long_chain(length):
    """Let's make it hard"""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    electricPowerType = F.ElectricPower.bind_typegraph(tg)
    ep = [electricPowerType.create_instance(g=g) for _ in range(length)]

    for i, (left, right) in enumerate(pairwise(ep)):
        if i % 2:
            left._is_interface.get().connect_to(right)
        else:
            left.lv.get()._is_interface.get().connect_to(right.lv.get())
            left.hv.get()._is_interface.get().connect_to(right.hv.get())

    assert ep[0]._is_interface.get().is_connected_to(ep[-1])
    assert ep[0].lv.get()._is_interface.get().is_connected_to(ep[-1].lv.get())
    assert ep[0].hv.get()._is_interface.get().is_connected_to(ep[-1].hv.get())


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

    class _Low(fabll.Node): ...

    class _High(fabll.Node):
        lower1: _Low
        lower2: _Low

    class _ShallowBridge(fabll.Node):
        high_in: _High
        high_out: _High

        def __preinit__(self) -> None:
            self.high_in.connect_shallow(self.high_out)

        @fabll.rt_field
        def can_bridge(self):
            return F.can_bridge(self.high_in, self.high_out)

    bridge = _ShallowBridge()
    high1 = _High()
    high2 = _High()
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

    class _Buffer(fabll.Node):
        ins: F.Electrical
        outs: F.Electrical

        ins_l: F.ElectricLogic
        outs_l: F.ElectricLogic

        def __preinit__(self) -> None:
            self.ins_l.signal.connect(self.ins)
            self.outs_l.signal.connect(self.outs)

            self.ins_l.connect_shallow(self.outs_l)

        _single_electric_reference = fabll._ChildField(F.has_single_electric_reference)

    l1 = F.ElectricLogic()
    l2 = F.ElectricLogic()
    b = _Buffer()

    l1.signal.connect(b.ins)
    l2.signal.connect(b.outs)
    b_ref = b._single_electric_reference.get().get_reference()
    l1.reference.get().connect(b_ref)
    l2.reference.get().connect(b_ref)

    assert l1.is_connected_to(l2)


def test_single_electric_reference_connects_children():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _WithReferences(fabll.Node):
        power_a = F.ElectricPower.MakeChild()
        power_b = F.ElectricPower.MakeChild()

        _single_electric_reference = fabll.Traits.MakeEdge(
            F.has_single_electric_reference.MakeChild()
        )

    app = _WithReferences.bind_typegraph(tg).create_instance(g=g)
    app._single_electric_reference.get().connect_all_references()
    shared_ref = app._single_electric_reference.get().get_reference()

    assert shared_ref._is_interface.get().is_connected_to(app.power_a.get())
    assert shared_ref._is_interface.get().is_connected_to(app.power_b.get())
    assert app.power_a.get()._is_interface.get().is_connected_to(app.power_b.get())


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
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _Buffer(fabll.Node):
        ins = [F.Electrical.MakeChild() for _ in range(2)]
        outs = [F.Electrical.MakeChild() for _ in range(2)]
        ins_l = [F.ElectricLogic.MakeChild() for _ in range(2)]
        outs_l = [F.ElectricLogic.MakeChild() for _ in range(2)]

        _single_electric_reference = fabll.Traits.MakeEdge(
            F.has_single_electric_reference.MakeChild()
        )

    class _UARTBuffer(fabll.Node):
        buf = _Buffer.MakeChild()
        bus_in = F.UART_Base.MakeChild()
        bus_out = F.UART_Base.MakeChild()

        _single_electric_reference = fabll.Traits.MakeEdge(
            F.has_single_electric_reference.MakeChild()
        )

    app = _UARTBuffer.bind_typegraph(tg).create_instance(g=g)

    for el, lo in chain(
        zip(app.buf.get().ins, app.buf.get().ins_l),
        zip(app.buf.get().outs, app.buf.get().outs_l),
    ):
        lo.get().line.get()._is_interface.get().connect_to(el.get())

    for l1, l2 in zip(app.buf.get().ins_l, app.buf.get().outs_l):
        l1.get()._is_interface.get().connect_shallow_to(l2.get())

    app.bus_in.get().tx.get().line.get()._is_interface.get().connect_to(
        app.buf.get().ins[0].get()
    )
    app.bus_in.get().rx.get().line.get()._is_interface.get().connect_to(
        app.buf.get().ins[1].get()
    )
    app.bus_out.get().tx.get().line.get()._is_interface.get().connect_to(
        app.buf.get().outs[0].get()
    )
    app.bus_out.get().rx.get().line.get()._is_interface.get().connect_to(
        app.buf.get().outs[1].get()
    )

    for x in fabll.Traits.get_implementors(
        F.has_single_electric_reference.bind_typegraph(tg), g
    ):
        x.connect_all_references()

    app._single_electric_reference.get().connect_all_references()

    bus_i = app.bus_in.get()
    bus_o = app.bus_out.get()
    buf = app.buf.get()

    # Check that the two buffer sides are not connected electrically
    assert not buf.ins[0].get()._is_interface.get().is_connected_to(buf.outs[0].get())
    assert not buf.ins[1].get()._is_interface.get().is_connected_to(buf.outs[1].get())
    assert (
        not bus_i.rx.get()
        .line.get()
        ._is_interface.get()
        .is_connected_to(bus_o.rx.get().line.get())
    )
    assert (
        not bus_i.tx.get()
        .line.get()
        ._is_interface.get()
        .is_connected_to(bus_o.tx.get().line.get())
    )

    # direct connect
    assert (
        bus_i.tx.get().line.get()._is_interface.get().is_connected_to(buf.ins[0].get())
    )
    assert (
        bus_i.rx.get().line.get()._is_interface.get().is_connected_to(buf.ins[1].get())
    )
    assert (
        bus_o.tx.get().line.get()._is_interface.get().is_connected_to(buf.outs[0].get())
    )
    assert (
        bus_o.rx.get().line.get()._is_interface.get().is_connected_to(buf.outs[1].get())
    )

    # connect through trait
    assert (
        buf.ins_l[0]
        .get()
        .reference.get()
        ._is_interface.get()
        .is_connected_to(buf.ins_l[0].get().reference.get())
    )
    assert (
        buf.ins_l[0]
        .get()
        .reference.get()
        ._is_interface.get()
        .is_connected_to(buf.outs_l[0].get().reference.get())
    )
    assert (
        buf.outs_l[1]
        .get()
        .reference.get()
        ._is_interface.get()
        .is_connected_to(buf.ins_l[0].get().reference.get())
    )
    assert (
        bus_i.rx.get()
        .reference.get()
        ._is_interface.get()
        .is_connected_to(bus_o.rx.get().reference.get())
    )

    # connect shallow
    assert buf.ins_l[0].get()._is_interface.get().is_connected_to(buf.outs_l[0].get())


# TODO requires up connect
# connect through up
# assert bus_i.tx.get()._is_interface.get().is_connected_to(buf.ins_l[0].get())
# assert bus_o.tx.get()._is_interface.get().is_connected_to(buf.outs_l[0].get())

# Check that the two buffer sides are connected logically
# assert bus_i.tx.get()._is_interface.get().is_connected_to(bus_o.tx.get())
# assert bus_i.rx.get()._is_interface.get().is_connected_to(bus_o.rx.get())
# assert bus_i._is_interface.get().is_connected_to(bus_o)


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
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    I2CType = F.I2C.bind_typegraph(tg)
    i2c1 = I2CType.create_instance(g=g)
    i2c2 = I2CType.create_instance(g=g)

    i2c1._is_interface.get().connect_to(i2c2)

    # I2C's connected
    assert i2c1._is_interface.get().is_connected_to(i2c2)

    # Electric signals connected
    assert i2c1.scl.get()._is_interface.get().is_connected_to(i2c2.scl.get())
    assert i2c1.sda.get()._is_interface.get().is_connected_to(i2c2.sda.get())

    assert ~i2c1.scl.get()._is_interface.get().is_connected_to(i2c2.sda.get())

    # Electricals connected
    assert (
        i2c1.scl.get()
        .line.get()
        ._is_interface.get()
        .is_connected_to(i2c2.scl.get().line.get())
    )
    assert (
        i2c1.sda.get()
        .line.get()
        ._is_interface.get()
        .is_connected_to(i2c2.sda.get().line.get())
    )

    # Electric powers connected
    assert (
        i2c1.scl.get()
        .reference.get()
        ._is_interface.get()
        .is_connected_to(i2c2.scl.get().reference.get())
    )
    assert (
        i2c1.sda.get()
        .reference.get()
        ._is_interface.get()
        .is_connected_to(i2c2.sda.get().reference.get())
    )

    # Electric powers electricals connected
    assert (
        i2c1.scl.get()
        .reference.get()
        .hv.get()
        ._is_interface.get()
        .is_connected_to(i2c2.scl.get().reference.get().hv.get())
    )
    assert (
        i2c1.scl.get()
        .reference.get()
        .lv.get()
        ._is_interface.get()
        .is_connected_to(i2c2.scl.get().reference.get().lv.get())
    )
    assert (
        i2c1.sda.get()
        .reference.get()
        .hv.get()
        ._is_interface.get()
        .is_connected_to(i2c2.sda.get().reference.get().hv.get())
    )
    assert (
        i2c1.sda.get()
        .reference.get()
        .lv.get()
        ._is_interface.get()
        .is_connected_to(i2c2.sda.get().reference.get().lv.get())
    )

    assert not (
        i2c1.scl.get().reference.get().hv.get()._is_interface.get()
    ).is_connected_to(i2c2.scl.get().reference.get().lv.get())
    assert not (
        i2c1.scl.get()
        .reference.get()
        .lv.get()
        ._is_interface.get()
        .is_connected_to(i2c2.scl.get().reference.get().hv.get())
    )
    assert not (
        i2c1.sda.get()
        .reference.get()
        .hv.get()
        ._is_interface.get()
        .is_connected_to(i2c2.sda.get().reference.get().lv.get())
    )
    assert not (
        i2c1.sda.get()
        .reference.get()
        .lv.get()
        ._is_interface.get()
        .is_connected_to(i2c2.sda.get().reference.get().hv.get())
    )


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
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    electricalType = F.Electrical.bind_typegraph(tg)
    electrical1 = electricalType.create_instance(g=g)
    electrical2 = electricalType.create_instance(g=g)
    electrical3 = electricalType.create_instance(g=g)

    electrical1._is_interface.get().connect_shallow_to(electrical2)
    electrical1._is_interface.get().connect_shallow_to(electrical3)
    assert electrical1._is_interface.get().is_connected_to(electrical2)
    assert electrical1._is_interface.get().is_connected_to(electrical3)


def test_is_interface_filter_requires_trait_on_target():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _Plain(fabll.Node):
        pass

    plain_type = _Plain.bind_typegraph(tg)
    with_trait = plain_type.create_instance(g=g)
    without_trait = plain_type.create_instance(g=g)

    with_trait_interface = fabll.Traits.create_and_add_instance_to(
        with_trait, fabll.is_interface
    )
    with_trait_interface.connect_to(without_trait)

    assert not with_trait_interface.is_connected_to(without_trait)


def test_connect_incompatible():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _A(fabll.Node):
        _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    class _B(fabll.Node):
        _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    aType = _A.bind_typegraph(tg)
    bType = _B.bind_typegraph(tg)
    a = aType.create_instance(g=g)
    b = bType.create_instance(g=g)

    with pytest.raises(ValueError, match="Failed to connect"):
        a._is_interface.get().connect_to(b)


def test_connect_incompatible_hierarchical():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _B(fabll.Node):
        _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())

    class _A(fabll.Node):
        _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
        b = _B.MakeChild()

    aType = _A.bind_typegraph(tg)
    bType = _B.bind_typegraph(tg)
    x = aType.create_instance(g=g)
    y = bType.create_instance(g=g)
    with pytest.raises(ValueError, match="Failed to connect"):
        x._is_interface.get().connect_to(y)


def test_connect_incompatible_hierarchical_regression():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    electricPowerType = F.ElectricPower.bind_typegraph(tg)
    electricalType = F.Electrical.bind_typegraph(tg)
    x = electricPowerType.create_instance(g=g)
    y = electricalType.create_instance(g=g)

    with pytest.raises(ValueError, match="Failed to connect"):
        x._is_interface.get().connect_to(y)


def test_sibling_connected():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _TestIf(fabll.Node):
        _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
        if1 = F.Electrical.MakeChild()
        if2 = F.Electrical.MakeChild()

    test_if = _TestIf.bind_typegraph(tg).create_instance(g=g)

    assert not test_if.if1.get()._is_interface.get().is_connected_to(test_if.if2.get())

    test_if.if1.get()._is_interface.get().connect_to(test_if.if2.get())

    assert test_if.if1.get()._is_interface.get().is_connected_to(test_if.if2.get())


class TestElectricPowerVccGndDeprecation:
    """
    Test deprecation warnings for vcc/gnd aliases in ElectricPower.

    vcc/gnd are always connected to hv/lv for backwards compatibility.
    The post_design check warns if external connections use these deprecated aliases.
    """

    def test_vcc_always_connected_to_hv(self):
        """
        vcc should always be connected to hv (not floating).
        """
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        power = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)

        # vcc should be connected to hv immediately (via MakeEdge)
        assert power.vcc.get()._is_interface.get().is_connected_to(power.hv.get())

    def test_gnd_always_connected_to_lv(self):
        """
        gnd should always be connected to lv (not floating).
        """
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        power = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)

        # gnd should be connected to lv immediately (via MakeEdge)
        assert power.gnd.get()._is_interface.get().is_connected_to(power.lv.get())

    def test_no_warning_when_vcc_gnd_not_externally_used(self):
        """
        No deprecation warning if nothing external connects to vcc/gnd.
        """
        from faebryk.libs.app.checks import check_design

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        power = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)

        # Should not raise any warning - vcc/gnd only have their hv/lv connections
        check_design(power, F.implements_design_check.CheckStage.POST_DESIGN)

    def test_warning_when_vcc_externally_used(self, caplog):
        """
        Deprecation warning should be raised if something external connects to vcc.
        """
        from faebryk.libs.app.checks import check_design

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        power = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)
        external = F.Electrical.bind_typegraph(tg).create_instance(g=g)

        # Connect something external to vcc (deprecated)
        external._is_interface.get().connect_to(power.vcc.get())

        # Run check - should warn about vcc usage
        with caplog.at_level(logging.WARNING):
            check_design(power, F.implements_design_check.CheckStage.POST_DESIGN)

        assert "vcc" in caplog.text
        assert "Deprecated" in caplog.text

    def test_warning_when_gnd_externally_used(self, caplog):
        """
        Deprecation warning should be raised if something external connects to gnd.
        """
        from faebryk.libs.app.checks import check_design

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        power = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)
        external = F.Electrical.bind_typegraph(tg).create_instance(g=g)

        # Connect something external to gnd (deprecated)
        external._is_interface.get().connect_to(power.gnd.get())

        # Run check - should warn about gnd usage
        with caplog.at_level(logging.WARNING):
            check_design(power, F.implements_design_check.CheckStage.POST_DESIGN)

        assert "gnd" in caplog.text
        assert "Deprecated" in caplog.text

    def test_external_to_vcc_reaches_hv(self):
        """
        Something connected to vcc should be able to reach hv.
        """
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        power = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)
        external = F.Electrical.bind_typegraph(tg).create_instance(g=g)

        # Connect external to vcc
        external._is_interface.get().connect_to(power.vcc.get())

        # External should be reachable from hv (through vcc)
        assert external._is_interface.get().is_connected_to(power.hv.get())

    def test_external_to_gnd_reaches_lv(self):
        """
        Something connected to gnd should be able to reach lv.
        """
        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        power = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)
        external = F.Electrical.bind_typegraph(tg).create_instance(g=g)

        # Connect external to gnd
        external._is_interface.get().connect_to(power.gnd.get())

        # External should be reachable from lv (through gnd)
        assert external._is_interface.get().is_connected_to(power.lv.get())

    def test_no_warning_when_using_hv_lv_directly(self, caplog):
        """
        Using hv/lv directly should not trigger deprecation warnings.
        """
        from faebryk.libs.app.checks import check_design

        g = graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        power = F.ElectricPower.bind_typegraph(tg).create_instance(g=g)
        external_hv = F.Electrical.bind_typegraph(tg).create_instance(g=g)
        external_lv = F.Electrical.bind_typegraph(tg).create_instance(g=g)

        # Connect directly to hv/lv (preferred usage)
        external_hv._is_interface.get().connect_to(power.hv.get())
        external_lv._is_interface.get().connect_to(power.lv.get())

        # Run check - should NOT warn
        with caplog.at_level(logging.WARNING):
            check_design(power, F.implements_design_check.CheckStage.POST_DESIGN)

        # No deprecation warning for hv/lv usage
        assert "Deprecated" not in caplog.text
