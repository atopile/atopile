# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import TYPE_CHECKING, Self

import faebryk.core.node as fabll
from faebryk.library import _F as F

if TYPE_CHECKING:
    from faebryk.library.ElectricPower import ElectricPower

logger = logging.getLogger(__name__)


class has_single_electric_reference(fabll.Node):
    """
    Connect all electric references of a module into a single reference.

    The trait provides a `reference` (ElectricPower) that can be accessed via
    `reference_shim` at compile time.

    What counts as an "electric reference" here is **not** "any ElectricPower
    anywhere". Instead, we look for `ElectricSignal`/`ElectricLogic` instances
    in the owning node's hierarchy and connect their `.reference` power rails
    to this trait's shared `reference`.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    # The ElectricPower reference that all children will be connected to
    reference = F.ElectricPower.MakeChild()

    # Whether to only connect the ground (lv) pins, not the full power rails
    ground_only_ = F.Parameters.BooleanParameter.MakeChild()

    # Design check to run connect_all_references automatically during POST_INSTANTIATION_SETUP
    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    def get_reference(self) -> "ElectricPower":
        """Get the shared ElectricPower reference."""
        return self.reference.get()

    @property
    def ground_only(self) -> bool:
        """Whether to only connect grounds (lv), not full power rails."""
        literal = self.ground_only_.get().try_extract_constrained_literal()
        if literal is None:
            return False
        return literal.get_single()

    @F.implements_design_check.register_post_instantiation_setup_check
    def __check_post_instantiation_setup__(self):
        self.connect_all_references()

    def connect_all_references(self):
        parent_node = self.get_parent_force()[0]
        ground_only = self.ground_only
        reference = self.reference.get()

        all_signals: list[fabll.Node] = parent_node.get_children(
            direct_only=False,
            types=(F.ElectricSignal, F.ElectricLogic),
        )

        if not all_signals:
            logger.debug(
                "No ElectricSignal/ElectricLogic children found in "
                f"{parent_node.get_name()}"
            )
            return

        for signal in all_signals:
            signal_reference: F.ElectricPower = signal.reference.get()  # type: ignore[attr-defined]
            if ground_only:
                signal_reference.lv.get()._is_interface.get().connect_to(
                    reference.lv.get()
                )
            else:
                signal_reference._is_interface.get().connect_to(reference)

    @classmethod
    def MakeChild(
        cls, ground_only: bool = False, exclude: list[fabll._ChildField] = []
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Booleans.MakeChild_SetSuperset(
                [out, cls.ground_only_], ground_only
            )
        )
        return out


# -----------------------------------------------------------------------------
#                                 Tests
# -----------------------------------------------------------------------------

import faebryk.core.faebrykpy as fbrk  # noqa: E402
import faebryk.core.graph as graph  # noqa: E402


def _iface_connected(a: fabll.Node, b: fabll.Node) -> bool:
    path = fbrk.EdgeInterfaceConnection.is_connected_to(
        source=a.instance, target=b.instance
    )
    return path.get_end_node().node().is_same(other=b.instance.node())


def test_has_single_electric_reference_connects_signal_references():
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _shared_ref = fabll.Traits.MakeEdge(has_single_electric_reference.MakeChild())

        a = F.ElectricLogic.MakeChild()
        b = F.ElectricSignal.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    trait = app.get_trait(has_single_electric_reference)
    shared = trait.reference.get()

    # Before unification, the signal references are distinct
    assert not _iface_connected(app.a.get().reference.get(), shared)
    assert not _iface_connected(app.b.get().reference.get(), shared)

    trait.connect_all_references()

    assert _iface_connected(app.a.get().reference.get(), shared)
    assert _iface_connected(app.b.get().reference.get(), shared)


def test_has_single_electric_reference_reaches_into_nested_nodes_with_own_trait():  # noqa: E501
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _Child(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _shared_ref = fabll.Traits.MakeEdge(has_single_electric_reference.MakeChild())
        logic = F.ElectricLogic.MakeChild()

    class _App(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _shared_ref = fabll.Traits.MakeEdge(has_single_electric_reference.MakeChild())
        child = _Child.MakeChild()
        top_logic = F.ElectricLogic.MakeChild()

    app = _App.bind_typegraph(tg=tg).create_instance(g=g)

    app_trait = app.get_trait(has_single_electric_reference)
    shared = app_trait.reference.get()

    app_trait.connect_all_references()

    # top-level logic should be unified with app's shared reference
    assert _iface_connected(app.top_logic.get().reference.get(), shared)

    # child's logic reference should ALSO be unified with parent's shared reference
    assert _iface_connected(app.child.get().logic.get().reference.get(), shared)
