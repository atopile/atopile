# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Keep-Picked-Parts: Logic for preserving PCB-sourced constraints.

This module handles the flow where parts previously picked and saved to a PCB
are reused in subsequent builds. If the design changes and conflicts with
the PCB constraints, the build will fail with an error.

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

    Used to trace which constraints came from the PCB file.
    If these constraints conflict with design constraints, the build will fail.

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
):
    """
    Load part constraints from PCB properties and set them on modules.

    This reads LCSC IDs and saved parameters from PCB footprint properties
    and sets them as constraints. If these constraints conflict with the
    design constraints, the build will fail with a solver Contradiction.
    """
    import faebryk.library._F as F
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

    footprint_map = PCB_Transformer.map_footprints(tg, pcb)

    for node, pcb_fp in footprint_map.items():
        module_path = node.get_full_name()

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
#  TESTS
# =============================================================================


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


def test_pcb_constraint_conflict_detection():
    """
    Test that conflicting PCB constraints (IsSuperset) cause a contradiction.

    Setup:
    - Design constraint: [8k, 12k] ohm (10kohm +/- 20%)
    - PCB constraint: IsSuperset([990, 1010] ohm) i.e., param must contain 1kohm

    Expected: Contradiction because [8k, 12k] doesn't contain [990, 1010].
    """
    import pytest

    from faebryk.core.solver.solver import Solver
    from faebryk.core.solver.utils import Contradiction
    from faebryk.libs.test.boundexpressions import BoundExpressions

    E = BoundExpressions()
    p0 = E.parameter_op(units=E.U.Ohm)

    # Design constraint: param is subset of [8k, 12k]
    E.is_subset(p0, E.lit_op_range(((8000, E.U.Ohm), (12000, E.U.Ohm))), assert_=True)

    # PCB constraint: param is superset of [990, 1010] (i.e., must contain 1kohm)
    # This is incompatible because [8k, 12k] doesn't contain [990, 1010]
    E.is_superset(p0, E.lit_op_range(((990, E.U.Ohm), (1010, E.U.Ohm))), assert_=True)

    solver = Solver()
    with pytest.raises(Contradiction):
        solver.simplify(E.tg, E.g)


def test_pcb_constraint_compatible():
    """
    Test that compatible PCB constraints don't raise errors.

    Setup:
    - Design constraint: [8k, 12k] ohm (10kohm +/- 20%)
    - PCB constraint: IsSuperset([9.9k, 10.1k] ohm) i.e., param must contain 10kohm

    Expected: No contradiction, since [8k, 12k] contains [9.9k, 10.1k].
    """
    from faebryk.core.solver.solver import Solver
    from faebryk.libs.test.boundexpressions import BoundExpressions

    E = BoundExpressions()
    p0 = E.parameter_op(units=E.U.Ohm)

    # Design constraint: param is subset of [8k, 12k]
    E.is_subset(p0, E.lit_op_range(((8000, E.U.Ohm), (12000, E.U.Ohm))), assert_=True)

    # PCB constraint: param is superset of [9.9k, 10.1k] (i.e., must contain 10kohm)
    # This is compatible because [8k, 12k] contains [9.9k, 10.1k]
    E.is_superset(p0, E.lit_op_range(((9900, E.U.Ohm), (10100, E.U.Ohm))), assert_=True)

    solver = Solver()
    # Should NOT raise Contradiction
    solver.simplify(E.tg, E.g)
