# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class requires_external_usage(fabll.Node):
    @property
    def fulfilled(self) -> bool:
        obj = fabll.Traits(self).get_obj_raw()
        parent = obj.get_parent()
        if parent is None:
            return True

        parent_node, _ = parent
        # TODO: disables checks for floating modules
        if parent_node.get_parent() is None:
            return True

        for node in obj.get_children(
            direct_only=False,
            types=fabll.Node,
            include_root=True,
            required_trait=fabll.is_interface,
        ):
            iface = node.get_trait(fabll.is_interface)
            for c, path in iface.get_connected().items():
                if path.length == 1 and not any(
                    parent_node.is_same(p) for p, _ in c.get_hierarchy()
                ):
                    return True

        return False

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    class RequiresExternalUsageNotFulfilled(
        F.implements_design_check.UnfulfilledCheckException
    ):
        def __init__(self, nodes: list[fabll.Node]):
            super().__init__(
                "Nodes requiring external usage but not used externally",
                nodes=nodes,
            )

    @F.implements_design_check.register_post_design_check
    def __check_post_design__(self):
        if not self.fulfilled:
            raise requires_external_usage.RequiresExternalUsageNotFulfilled(
                nodes=[fabll.Traits(self).get_obj_raw()],
            )


class Test:
    def test_requires_external_usage(self):
        import pytest

        import faebryk.core.faebrykpy as fbrk
        from faebryk.libs.app.checks import check_design
        from faebryk.libs.exceptions import UserDesignCheckException

        g = fabll.graph.GraphView.create()
        tg = fbrk.TypeGraph.create(g=g)

        class Inner(fabll.Node):
            b = F.Electrical.MakeChild()

        class Outer(fabll.Node):
            a = F.Electrical.MakeChild()
            inner = Inner.MakeChild()
            _requires_external_usage = fabll.Traits.MakeEdge(
                requires_external_usage.MakeChild(),
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
            check_design(app, stage=F.implements_design_check.CheckStage.POST_DESIGN)
        if isinstance(excinfo.value, ExceptionGroup):
            assert excinfo.group_contains(
                UserDesignCheckException,
                match="Nodes requiring external usage but not used externally",
            )

        # internal connection
        outer1.a.get()._is_interface.get().connect_to(outer1.inner.get().b.get())
        with pytest.raises((ExceptionGroup, UserDesignCheckException)) as excinfo:
            check_design(app, stage=F.implements_design_check.CheckStage.POST_DESIGN)
        if isinstance(excinfo.value, ExceptionGroup):
            assert excinfo.group_contains(
                UserDesignCheckException,
                match="Nodes requiring external usage but not used externally",
            )

        # path to external (still internal-only for `a`)
        outer1.inner.get().b.get()._is_interface.get().connect_to(outer2.a.get())
        with pytest.raises((ExceptionGroup, UserDesignCheckException)) as excinfo:
            check_design(app, stage=F.implements_design_check.CheckStage.POST_DESIGN)
        if isinstance(excinfo.value, ExceptionGroup):
            assert excinfo.group_contains(
                UserDesignCheckException,
                match="Nodes requiring external usage but not used externally",
            )

        # direct external connection also satisfies the requirement
        outer1.a.get()._is_interface.get().connect_to(outer2.inner.get().b.get())
        check_design(app, stage=F.implements_design_check.CheckStage.POST_DESIGN)
