# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Keep-Picked-Parts: Logic for preserving and invalidating PCB-sourced constraints.

This module handles the flow where parts previously picked and saved to a PCB
are reused in subsequent builds.

NOTE: Traits use lazy imports for F.* to avoid circular imports. By the time
the trait methods are called, _F is fully loaded (since callers must have
imported F to get the module types they're working with).
"""

from __future__ import annotations

import json
import logging
from enum import StrEnum
from typing import Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
from faebryk.libs.kicad.fileformats import Property, kicad

logger = logging.getLogger(__name__)

NO_LCSC_DISPLAY = "No LCSC number"


# =============================================================================
#  TRAITS
# =============================================================================


class has_pcb_source(fabll.Node):
    """
    Marks a constraint or picking trait as loaded from PCB data.

    Attached to:
    - is_pickable_by_supplier_id traits (LCSC ID from PCB)
    - is_pickable_by_part_number traits (MFR/MPN from PCB)
    - IsSuperset expressions (parameter values from PCB)

    Used to trace which constraints came from the PCB file,
    enabling invalidation when they conflict with the design.

    NOTE: Children (StringParameters) are created in setup() using
    Literals.Strings for the value. This avoids circular imports since
    the lazy import happens when setup() is called, not at module load.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def setup(
        self,
        source_file: str,
        module_path: str,
        param_name: str = "",
    ) -> Self:
        # Lazy import to avoid circular import at module load time
        import faebryk.library._F as F

        g = self.g
        tg = self.tg

        # Create StringParameter children and set their values
        # Using the Literals.Strings pattern for setting superset
        source_file_param = F.Parameters.StringParameter.bind_typegraph(
            tg
        ).create_instance(g)
        source_file_param.set_superset(source_file)
        self.add_child(source_file_param, "source_file_")

        module_path_param = F.Parameters.StringParameter.bind_typegraph(
            tg
        ).create_instance(g)
        module_path_param.set_superset(module_path)
        self.add_child(module_path_param, "module_path_")

        param_name_param = F.Parameters.StringParameter.bind_typegraph(
            tg
        ).create_instance(g)
        param_name_param.set_superset(param_name)
        self.add_child(param_name_param, "param_name_")

        return self

    def _get_string_child(self, identifier: str) -> str:
        """Get a child StringParameter value by identifier."""
        import faebryk.library._F as F

        child = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier=identifier
        )
        if child is None:
            return ""
        return F.Parameters.StringParameter(instance=child).extract_singleton()

    @property
    def source_file(self) -> str:
        return self._get_string_child("source_file_")

    @property
    def module_path(self) -> str:
        return self._get_string_child("module_path_")

    @property
    def param_name(self) -> str | None:
        name = self._get_string_child("param_name_")
        return name if name else None

    def is_param_constraint(self) -> bool:
        return bool(self.param_name)


class has_pcb_pick_contradiction(fabll.Node):
    """
    Marks a PCB-sourced pick that contradicts the current design.

    When a PCB pick conflicts with design constraints, we mark it
    with this trait so the picker skips it and re-picks fresh.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class is_invalidated_pcb_constraint(fabll.Node):
    """
    Marks a PCB-sourced parameter constraint as invalidated.

    When attached to an expression (e.g., IsSuperset), get_operations()
    will filter it out so force_extract_superset() returns the correct value
    without the stale PCB constraint.

    This is separate from has_pcb_pick_contradiction which marks picking traits.
    This trait marks the actual parameter constraint expressions.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


# =============================================================================
#  PCB PROPERTY NAMES
# =============================================================================


class Properties(StrEnum):
    manufacturer = "Manufacturer"
    manufacturer_partno = "Partnumber"
    supplier_partno = "LCSC"
    param_prefix = "PARAM_"
    param_wildcard = "PARAM_*"


# =============================================================================
#  LOAD FROM PCB
# =============================================================================


def load_part_info_from_pcb(
    pcb: kicad.pcb.KicadPcb,
    tg: fbrk.TypeGraph,
    source_file: str = "",
    skip_modules: set[str] | None = None,
):
    """Load part constraints from PCB properties and set them on modules."""
    import faebryk.library._F as F

    if skip_modules is None:
        skip_modules = set()
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

    footprint_map = PCB_Transformer.map_footprints(tg, pcb)

    for node, pcb_fp in footprint_map.items():
        module_path = node.get_full_name()

        if module_path in skip_modules:
            logger.info(f"Skipping invalidated PCB constraints for {module_path}")
            continue

        if node.has_trait(F.Pickable.has_part_picked):
            continue
        if node.has_trait(F.has_part_removed):
            continue

        lcsc_id = Property.try_get_property(
            pcb_fp.propertys, Properties.supplier_partno
        )
        if lcsc_id == NO_LCSC_DISPLAY:
            lcsc_id = None

        manufacturer = Property.try_get_property(
            pcb_fp.propertys, Properties.manufacturer
        )
        partno = Property.try_get_property(
            pcb_fp.propertys, Properties.manufacturer_partno
        )

        if lcsc_id:
            supplier_trait = fabll.Traits.create_and_add_instance_to(
                node=node, trait=F.Pickable.is_pickable_by_supplier_id
            ).setup(
                supplier_part_id=lcsc_id,
                supplier=F.Pickable.is_pickable_by_supplier_id.Supplier.LCSC,
            )
            fabll.Traits.create_and_add_instance_to(
                supplier_trait, has_pcb_source
            ).setup(source_file=source_file, module_path=module_path)
            logger.debug(f"Set LCSC constraint {lcsc_id} on {node.get_name()}")
        elif manufacturer and partno:
            partno_trait = fabll.Traits.create_and_add_instance_to(
                node=node, trait=F.Pickable.is_pickable_by_part_number
            ).setup(manufacturer=manufacturer, partno=partno)
            fabll.Traits.create_and_add_instance_to(partno_trait, has_pcb_source).setup(
                source_file=source_file, module_path=module_path
            )
            logger.debug(f"Set part number constraint {manufacturer}/{partno}")
        else:
            logger.warning(f"No part info found in PCB for {node.get_name()}")
            continue

        # Load saved parameters as subset constraints
        for prop in pcb_fp.propertys:
            if not prop.name.startswith(Properties.param_prefix):
                continue

            param_name = prop.name.removeprefix(Properties.param_prefix)
            param_child = fbrk.EdgeComposition.get_child_by_identifier(
                bound_node=node.instance, child_identifier=param_name
            )
            if param_child is None:
                continue
            param = fabll.Node.bind_instance(param_child)
            if not param.has_trait(F.Parameters.is_parameter):
                continue

            try:
                param_value = json.loads(prop.value)
            except (json.JSONDecodeError, TypeError):
                logger.debug(f"Failed to parse PARAM_{param_name} value: {prop.value}")
                continue

            if param_value is None:
                logger.debug(f"Null value for PARAM_{param_name}, skipping")
                continue

            try:
                param_lit = F.Literals.is_literal.deserialize(
                    param_value, g=node.g, tg=node.tg
                )
            except Exception as e:
                logger.debug(f"Failed to deserialize PARAM_{param_name}: {e}")
                continue

            param_op = param.get_trait(F.Parameters.is_parameter_operatable)
            constraint = (
                F.Expressions.IsSuperset.bind_typegraph(tg=node.tg)
                .create_instance(g=node.g)
                .setup(
                    param_op.as_operand.get(),
                    param_lit.as_operand.get(),
                    assert_=True,
                )
            )
            fabll.Traits.create_and_add_instance_to(constraint, has_pcb_source).setup(
                source_file=source_file,
                module_path=module_path,
                param_name=param_name,
            )
            logger.debug(f"Set parameter constraint {param_name} on {node.get_name()}")


# =============================================================================
#  PCB CONSTRAINT QUERIES
# =============================================================================


def get_pcb_sourced_constraints(
    tg: fbrk.TypeGraph,
) -> list[tuple[fabll.Node, has_pcb_source]]:
    """Find all constraints/traits tagged with has_pcb_source."""
    results: list[tuple[fabll.Node, has_pcb_source]] = []
    pcb_source_type = has_pcb_source.bind_typegraph(tg)
    for pcb_source in pcb_source_type.get_instances():
        owner = fabll.Traits(pcb_source).get_obj_raw()
        results.append((owner, pcb_source))
    return results


# =============================================================================
#  CONTRADICTION DETECTION
# =============================================================================


def get_pcb_sources_from_contradiction(
    contradiction: Exception, tg: fbrk.TypeGraph
) -> list[has_pcb_source]:
    """
    Find PCB-sourced constraints involved in a solver Contradiction.

    When picking fails, this identifies which PCB-loaded constraints
    contributed to the contradiction so they can be marked stale.
    """
    import faebryk.library._F as F
    from faebryk.core.solver.utils import Contradiction

    involved: list[has_pcb_source] = []

    if not isinstance(contradiction, Contradiction):
        return involved

    all_pcb_constraints = get_pcb_sourced_constraints(tg)
    if not all_pcb_constraints:
        return involved

    for owner, pcb_source in all_pcb_constraints:
        if not pcb_source.is_param_constraint():
            if pcb_source not in involved:
                involved.append(pcb_source)
            continue

        if not owner.has_trait(F.Expressions.is_expression):
            continue

        expr = owner.get_trait(F.Expressions.is_expression)
        operands = expr.get_operands()

        param_po = None
        pcb_literal = None
        for operand in operands:
            if po := operand.as_parameter_operatable.try_get():
                param_po = po
            elif lit := operand.as_literal.try_get():
                pcb_literal = lit

        if not param_po or not pcb_literal:
            continue

        all_ops = param_po.get_operations(predicates_only=True)
        for op in all_ops:
            try:
                op_node = fabll.Traits(op).get_obj_raw()
            except (AssertionError, AttributeError):
                continue

            if op_node.has_trait(has_pcb_source):
                continue

            if op_expr := op.try_get_sibling_trait(F.Expressions.is_expression):
                for op_operand in op_expr.get_operands():
                    if other_lit := op_operand.as_literal.try_get():
                        try:
                            intersection = F.Literals.is_literal.op_setic_intersect(
                                pcb_literal, other_lit
                            )
                            if intersection.op_setic_is_empty():
                                if pcb_source not in involved:
                                    involved.append(pcb_source)
                        except Exception:
                            pass

    return involved


# =============================================================================
#  INVALIDATION
# =============================================================================


def mark_contradicting_pcb_picks(tg: fbrk.TypeGraph, module_paths: set[str]) -> int:
    """
    Mark PCB picks that contradict the current design.

    Called when solver finds a contradiction involving PCB constraints.
    Marks both:
    - Picking traits (is_pickable_by_supplier_id, is_pickable_by_part_number)
    - Parameter constraints (IsSuperset expressions)

    Also removes has_part_picked from affected modules so they can be re-picked.

    The picker will skip traits marked with has_pcb_pick_contradiction,
    falling back to parametric picking.

    Args:
        tg: TypeGraph
        module_paths: Modules whose PCB picks contradict the design

    Returns:
        Number of picks marked
    """
    import faebryk.library._F as F

    if not module_paths:
        return 0

    count = 0
    modules_cleared: set[str] = set()

    for owner, pcb_source in get_pcb_sourced_constraints(tg):
        if pcb_source.module_path not in module_paths:
            continue

        module_path = pcb_source.module_path

        # Skip if already marked
        if owner.has_trait(has_pcb_pick_contradiction):
            continue

        # Mark as contradicting for picker
        fabll.Traits.create_and_add_instance_to(owner, has_pcb_pick_contradiction)

        if pcb_source.is_param_constraint():
            # Parameter constraint - mark as invalidated
            # so get_operations() filters it out
            # owner IS the expression node (has_pcb_source was attached to it)
            fabll.Traits.create_and_add_instance_to(
                owner, is_invalidated_pcb_constraint
            )
            # Also mark as is_irrelevant so the solver ignores it
            from faebryk.core.solver.mutator import is_irrelevant

            fabll.Traits.create_and_add_instance_to(owner, is_irrelevant)
            logger.debug(f"Marked: {module_path}.{pcb_source.param_name}")
        else:
            # Picking trait - also mark has_part_picked on the module
            # so the picker knows to re-pick it
            picking_trait_owner = fabll.Traits(owner).get_obj_raw()
            if (
                picking_trait_owner.has_trait(F.Pickable.has_part_picked)
                and module_path not in modules_cleared
            ):
                part_picked = picking_trait_owner.get_trait(F.Pickable.has_part_picked)
                fabll.Traits.create_and_add_instance_to(
                    part_picked, has_pcb_pick_contradiction
                )
                modules_cleared.add(module_path)
                logger.debug(f"Marked has_part_picked for re-pick: {module_path}")

            logger.debug(f"Marked contradiction: {module_path} picking trait")

        count += 1

    if count > 0:
        logger.info(
            f"Marked {count} contradicting PCB picks for: "
            f"{', '.join(sorted(module_paths))}"
        )

    return count


# =============================================================================
#  TESTS
# =============================================================================


def test_is_invalidated_pcb_constraint_filters_get_operations():
    """
    Test that marking an expression with is_invalidated_pcb_constraint
    causes get_operations() to filter it out.
    """
    import faebryk.library._F as F
    from faebryk.library.Literals import Numbers
    from faebryk.libs.test.boundexpressions import BoundExpressions

    E = BoundExpressions()

    # Create parameter with two constraints
    param_op = E.parameter_op(units=E.U.Ohm)
    param_po = param_op.as_parameter_operatable.force_get()

    # PCB constraint: 4.7kohm (will be invalidated)
    pcb_lit = E.lit_op_single((4700, E.U.Ohm))
    pcb_expr = E.is_subset(param_op, pcb_lit, assert_=True)

    # Design constraint: 10kohm
    design_lit = E.lit_op_single((10000, E.U.Ohm))
    E.is_subset(param_op, design_lit, assert_=True)

    # Before invalidation: 3 IsSubset constraints (2 + domain)
    ops_before = param_po.get_operations(
        types=F.Expressions.IsSubset, predicates_only=True
    )
    assert len(ops_before) >= 2, f"Expected >=2, got {len(ops_before)}"

    # Intersection is empty (contradicting)
    lit_before = param_po.try_extract_superset()
    assert lit_before is not None
    lit_nums_before = fabll.Traits(lit_before).get_obj(Numbers)
    assert lit_nums_before.is_empty(), "Expected empty before invalidation"

    # Mark PCB constraint as invalidated
    pcb_expr_node = fabll.Traits(
        pcb_expr.as_parameter_operatable.force_get()
    ).get_obj_raw()
    fabll.Traits.create_and_add_instance_to(
        pcb_expr_node, is_invalidated_pcb_constraint
    )

    # After invalidation: one fewer constraint visible
    ops_after = param_po.get_operations(
        types=F.Expressions.IsSubset, predicates_only=True
    )
    assert len(ops_after) == len(ops_before) - 1

    # Now extraction should return 10kohm
    lit_after = param_po.try_extract_superset()
    assert lit_after is not None
    lit_nums_after = fabll.Traits(lit_after).get_obj(Numbers)
    assert not lit_nums_after.is_empty(), "Expected non-empty after invalidation"
    values = lit_nums_after.get_values()
    assert values == [10000.0, 10000.0], f"Expected [10000, 10000], got {values}"


def test_mark_contradicting_pcb_picks():
    """Test that mark_contradicting_pcb_picks correctly marks constraints."""
    import faebryk.library._F as F
    from faebryk.libs.test.boundexpressions import BoundExpressions

    E = BoundExpressions()

    # Create parameter
    param_op = E.parameter_op(units=E.U.Ohm)
    param_po = param_op.as_parameter_operatable.force_get()

    # Create IsSubset constraint and tag it as PCB-sourced
    pcb_lit = E.lit_op_single((4700, E.U.Ohm))
    pcb_expr = E.is_subset(param_op, pcb_lit, assert_=True)
    pcb_expr_po = pcb_expr.as_parameter_operatable.force_get()
    pcb_expr_node = fabll.Traits(pcb_expr_po).get_obj_raw()

    # Attach has_pcb_source trait
    fabll.Traits.create_and_add_instance_to(pcb_expr_node, has_pcb_source).setup(
        source_file="test.kicad_pcb",
        module_path="App.r1",
        param_name="resistance",
    )

    # Verify PCB source is found
    pcb_sources = get_pcb_sourced_constraints(E.tg)
    assert len(pcb_sources) == 1
    owner, pcb_source = pcb_sources[0]
    assert pcb_source.module_path == "App.r1"
    assert pcb_source.param_name == "resistance"
    assert pcb_source.is_param_constraint()

    # Mark as contradicting
    count = mark_contradicting_pcb_picks(E.tg, {"App.r1"})
    assert count == 1

    # Verify traits were added
    assert owner.has_trait(has_pcb_pick_contradiction)
    assert owner.has_trait(is_invalidated_pcb_constraint)

    # Verify constraint is now filtered out of get_operations
    ops = param_po.get_operations(types=F.Expressions.IsSubset, predicates_only=True)
    # The PCB constraint should not be in the results - it should have fewer ops
    # than before (we only added 1 IsSubset and it should be filtered now)
    for op in ops:
        # Check that the op itself doesn't have the invalidated trait
        assert not op.has_trait(is_invalidated_pcb_constraint), (
            "Invalidated constraint should be filtered"
        )


def test_has_pcb_source_trait():
    """Test has_pcb_source trait setup and properties."""
    import faebryk.core.graph as graph

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    # Create a dummy node to attach trait to
    dummy = fabll.Node.bind_typegraph(tg).create_instance(g)

    # Attach has_pcb_source
    pcb_source = fabll.Traits.create_and_add_instance_to(dummy, has_pcb_source).setup(
        source_file="/path/to/layout.kicad_pcb",
        module_path="App.sensor.i2c",
        param_name="address",
    )

    assert pcb_source.source_file == "/path/to/layout.kicad_pcb"
    assert pcb_source.module_path == "App.sensor.i2c"
    assert pcb_source.param_name == "address"
    assert pcb_source.is_param_constraint()

    # Test without param_name (picking trait, not param constraint)
    dummy2 = fabll.Node.bind_typegraph(tg).create_instance(g)
    pcb_source2 = fabll.Traits.create_and_add_instance_to(dummy2, has_pcb_source).setup(
        source_file="/path/to/layout.kicad_pcb",
        module_path="App.r1",
    )
    assert pcb_source2.param_name is None
    assert not pcb_source2.is_param_constraint()


def test_get_pcb_sourced_constraints():
    """Test querying PCB-sourced constraints from the graph."""
    import faebryk.core.graph as graph

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    # Initially empty
    assert get_pcb_sourced_constraints(tg) == []

    # Add some PCB-sourced constraints
    node1 = fabll.Node.bind_typegraph(tg).create_instance(g)
    node2 = fabll.Node.bind_typegraph(tg).create_instance(g)

    fabll.Traits.create_and_add_instance_to(node1, has_pcb_source).setup(
        source_file="test.pcb", module_path="App.r1"
    )
    fabll.Traits.create_and_add_instance_to(node2, has_pcb_source).setup(
        source_file="test.pcb", module_path="App.r2", param_name="resistance"
    )

    results = get_pcb_sourced_constraints(tg)
    assert len(results) == 2

    module_paths = {pcb_src.module_path for _, pcb_src in results}
    assert module_paths == {"App.r1", "App.r2"}


def test_include_invalidated_parameter():
    """Test that include_invalidated=True returns all operations."""
    import faebryk.library._F as F
    from faebryk.libs.test.boundexpressions import BoundExpressions

    E = BoundExpressions()

    param_op = E.parameter_op(units=E.U.Ohm)
    param_po = param_op.as_parameter_operatable.force_get()

    # Create two constraints
    lit1 = E.lit_op_single((100, E.U.Ohm))
    lit2 = E.lit_op_single((200, E.U.Ohm))
    expr1 = E.is_subset(param_op, lit1, assert_=True)
    E.is_subset(param_op, lit2, assert_=True)

    # Mark one as invalidated
    expr1_node = fabll.Traits(expr1.as_parameter_operatable.force_get()).get_obj_raw()
    fabll.Traits.create_and_add_instance_to(expr1_node, is_invalidated_pcb_constraint)

    # Default: invalidated filtered out
    ops_default = param_po.get_operations(
        types=F.Expressions.IsSubset, predicates_only=True
    )

    # With include_invalidated=True: all returned
    ops_all = param_po.get_operations(
        types=F.Expressions.IsSubset, predicates_only=True, include_invalidated=True
    )

    assert len(ops_all) == len(ops_default) + 1
