# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Any

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.zig.gen.faebryk.pointer import EdgePointer
from faebryk.libs.util import KeyErrorNotFound, not_none

logger = logging.getLogger(__name__)


class has_pin_association_heuristic_lookup_table(fabll.Node):
    mapping = fabll.ChildField(fabll.Parameter)
    accept_prefix = fabll.ChildField(fabll.Parameter)
    case_sensitive = fabll.ChildField(fabll.Parameter)
    nc = fabll.ChildField(fabll.Parameter)

    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    @classmethod
    def MakeChild(
        cls,
        mapping: dict[fabll.ChildField, list[str]],
        accept_prefix: bool,
        case_sensitive: bool,
        nc: list[str] = ["NC", "nc"],
    ) -> fabll.ChildField[Any]:
        out = fabll.ChildField(cls)
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral(  # TODO: Change to make literal bool
                [out, cls.accept_prefix], str(accept_prefix)
            )
        )
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral(
                [out, cls.case_sensitive], str(case_sensitive)
            )
        )
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral([out, cls.nc], nc)
        )
        for param_ref, param_names in mapping.items():
            # Add a set node for pin association table
            pin_association_table_set = fabll.Set.MakeChild()
            out.add_dependant(pin_association_table_set)
            for param_name in param_names:
                # Add an edge to the pin association table for each alternate name
                field = fabll.EdgeField(
                    [pin_association_table_set],
                    [fabll.LiteralNode.MakeChild(value=param_name)],
                    edge=EdgePointer.build(identifier=param_name, order=None),
                )
                out.add_dependant(field)
        return out

    def get_mapping_as_dict(self) -> dict[F.Electrical, list[str]]:
        mapping = {}
        pin_association_table_sets = self.get_children(
            direct_only=True, types=fabll.Set
        )
        for pin_association_table_set in pin_association_table_sets:
            electrical_bnode = not_none(
                EdgePointer.get_pointed_node_by_identifier(
                    bound_node=pin_association_table_set.instance,
                    identifier="electrical",
                )
            )
            associated_names: list[str] = []
            EdgePointer.visit_pointed_edges(
                bound_node=electrical_bnode,
                ctx=associated_names,
                f=lambda ctx, edge: ctx.append(
                    str(edge.edge().target().get_dynamic_attrs().get("value", ""))
                ),
            )
            mapping[F.Electrical.bind_instance(electrical_bnode)] = associated_names
        return mapping

    def get_pins(
        self,
        pins: list[tuple[str, str]],
    ) -> dict[str, F.Electrical]:
        """
        Get the pinmapping for a list of pins based on a lookup table.

        :param pins: A list of tuples with the pin number and name.
        :return: A dictionary with the pin name as key and the module interface as value
        """
        mapping = self.get_mapping_as_dict()
        accept_prefix = not_none(
            self.accept_prefix.get().try_extract_constrained_literal()
        )
        case_sensitive = not_none(
            self.case_sensitive.get().try_extract_constrained_literal()
        )
        nc = [
            not_none(self.nc.get().try_extract_constrained_literal())
        ]  # TODO: convert nc to list of str

        pinmap = {}
        for mif, alt_names in mapping.items():
            matches = []
            for number, name in pins:
                if name in nc:
                    continue
                for alt_name in alt_names:
                    if not case_sensitive:
                        alt_name = alt_name.lower()
                        name = name.lower()
                    if accept_prefix and name.endswith(alt_name):
                        matches.append((number, name))
                        break
                    elif name == alt_name:
                        matches.append((number, name))
                        break
            if not matches:
                try:
                    _, is_optional = mif.get_parent_with_trait(F.is_optional)
                    if not is_optional.is_needed():
                        is_optional._handle_result(False)
                        continue
                except KeyErrorNotFound:
                    pass
                raise F.has_pin_association_heuristic.PinMatchException(
                    f"Could not find a match for pin {mif} with names '{alt_names}'"
                    f" in the pins: {pins}"
                )
            for number, name in matches:
                pinmap[number] = mif
                logger.debug(
                    f"Matched pin {number} with name {name} to {mif} with "
                    f"alias {alt_names}"
                )

        unmatched = [p for p in pins if p[0] not in pinmap and p[1] not in nc]
        if unmatched:
            logger.warning(
                f"Unmatched pins: {unmatched}, all pins: {pins}, mapping: {mapping}"
            )
        return pinmap
