# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.app.checks import check_design
from faebryk.libs.exceptions import UserDesignCheckException

logger = logging.getLogger(__name__)


def test_requires_external_usage():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class Inner(fabll.Node):
        b = F.Electrical.MakeChild()

    class Outer(fabll.Node):
        a = F.Electrical.MakeChild()
        inner = Inner.MakeChild()
        _requires_external_usage = fabll.Traits.MakeEdge(
            F.requires_external_usage.MakeChild(),
            owner=[a],
        )

    class App(fabll.Node):
        outer1 = Outer.MakeChild()
        outer2 = Outer.MakeChild()

    app = App.bind_typegraph(tg=tg).create_instance(g=g)

    outer1 = app.outer1.get()
    outer2 = app.outer2.get()

    # no connections
    with pytest.raises((ExceptionGroup, UserDesignCheckException)) as excinfo:
        check_design(tg, stage=F.implements_design_check.CheckStage.POST_DESIGN)
    if isinstance(excinfo.value, ExceptionGroup):
        assert excinfo.group_contains(
            UserDesignCheckException,
            match="Nodes requiring external usage but not used externally",
        )

    # internal connection
    outer1.a.get()._is_interface.get().connect_to(outer1.inner.get().b.get())
    with pytest.raises((ExceptionGroup, UserDesignCheckException)) as excinfo:
        check_design(tg, stage=F.implements_design_check.CheckStage.POST_DESIGN)
    if isinstance(excinfo.value, ExceptionGroup):
        assert excinfo.group_contains(
            UserDesignCheckException,
            match="Nodes requiring external usage but not used externally",
        )

    # path to external (still internal-only for `a`)
    outer1.inner.get().b.get()._is_interface.get().connect_to(outer2.a.get())
    with pytest.raises((ExceptionGroup, UserDesignCheckException)) as excinfo:
        check_design(tg, stage=F.implements_design_check.CheckStage.POST_DESIGN)
    if isinstance(excinfo.value, ExceptionGroup):
        assert excinfo.group_contains(
            UserDesignCheckException,
            match="Nodes requiring external usage but not used externally",
        )

    # direct external connection also satisfies the requirement
    outer1.a.get()._is_interface.get().connect_to(outer2.inner.get().b.get())
    check_design(tg, stage=F.implements_design_check.CheckStage.POST_DESIGN)
