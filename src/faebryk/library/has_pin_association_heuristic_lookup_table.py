# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Any

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import KeyErrorNotFound

logger = logging.getLogger(__name__)


class has_pin_association_heuristic_lookup_table(fabll.Node):
    # TODO: Implement case sensitive get literal and accept prefix get literal
    """
    All literals, sets and tuples are children of the
    "out" parent node.
    nc_set
    |- nc_literal1
    |- nc_literal2

    mapping_set
    |- pat_tuple1
    |  |- pointer
    |  |  |- electrical1
    |  |- literals
    |  |  |- literal1
    |  |  |- literal2
    |- pat_tuple2
    |  |- pointer
    |  |  |- electrical2
    |  |- literals
    |  |  |- literal1
    |  |  |- literal2
    """

    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    mapping = F.Collections.PointerSet.MakeChild()
    accept_prefix_ = fabll.ChildField(fabll.Parameter)
    case_sensitive_ = fabll.ChildField(fabll.Parameter)
    nc = F.Collections.PointerSet.MakeChild()

    @classmethod
    def MakeChild(
        cls,
        mapping: dict[fabll.ChildField, list[str]],
        accept_prefix: bool,
        case_sensitive: bool,
        nc_in: list[str] = ["NC", "nc"],
    ) -> fabll.ChildField[Any]:
        out = fabll.ChildField(cls)
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral(
                [out, cls.accept_prefix_], accept_prefix
            )
        )
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral(
                [out, cls.case_sensitive_], case_sensitive
            )
        )
        nc_makechilds = []
        for nc_literal in nc_in:
            nc_lit = fabll.LiteralNode.MakeChild(value=nc_literal)
            out.add_dependant(nc_lit)
            nc_makechilds.append([nc_lit])
        nc_set_fields = F.Collections.PointerSet.EdgeFields(
            [out, cls.nc], nc_makechilds
        )
        out.add_dependant(*nc_set_fields)

        pat_tuples = []
        # Make literals and sets
        for child_field, param_names in mapping.items():
            pat_tuple = F.Collections.PointerTuple.MakeChild()
            out.add_dependant(pat_tuple)
            out.add_dependant(
                F.Collections.PointerTuple.SetPointer(
                    tup_ref=[pat_tuple], elem_ref=[child_field]
                )
            )
            for param_literal in param_names:
                param_lit = fabll.LiteralNode.MakeChild(value=param_literal)
                out.add_dependant(param_lit)
                out.add_dependant(
                    F.Collections.PointerTuple.AppendLiteral(
                        tup_ref=[pat_tuple], elem_ref=[param_lit]
                    )
                )

            pat_tuples.append([pat_tuple])

        # Populate mapping set with pat sets
        pat_set_edges = F.Collections.PointerSet.EdgeFields(
            [out, cls.mapping], pat_tuples
        )
        out.add_dependant(*pat_set_edges)

        return out

    def get_nc_literals(self) -> list[fabll.LiteralT]:
        nc_list = self.nc.get().as_list()
        nc_literals = [
            fabll.LiteralNode.bind_instance(instance=nc_lit.instance).get_value()
            for nc_lit in nc_list
        ]
        return nc_literals

    def get_mapping_as_dict(self) -> dict[F.Electrical, list[str]]:
        mapping: dict[F.Electrical, list[str]] = {}
        mapping_set = self.mapping.get()
        pat_tuples = mapping_set.as_list()
        for pat_tuple in pat_tuples:
            tuple_instance = F.Collections.PointerTuple.bind_instance(
                instance=pat_tuple.instance
            )
            elements = tuple_instance.get_literals_as_list()
            electrical = tuple_instance.deref_pointer()
            mapping[electrical] = elements  # type: ignore
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
        accept_prefix = self.accept_prefix_.get().try_extract_constrained_literal()
        case_sensitive = self.case_sensitive_.get().try_extract_constrained_literal()
        nc = self.get_nc_literals()

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
