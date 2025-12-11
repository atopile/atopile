# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import StrEnum

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.zig.gen.graph.graph import BoundNode  # type: ignore[import-untyped]
from faebryk.libs.util import not_none


class is_pickable_by_type(fabll.Node):
    """
    Marks a module as being parametrically selectable using the given parameters.

    Must map to an existing API endpoint.

    Should be named "pickable" to aid overriding by subclasses.
    """

    class Endpoint(StrEnum):
        """Query endpoints known to the API."""

        RESISTORS = "resistors"
        CAPACITORS = "capacitors"
        INDUCTORS = "inductors"

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    endpoint_ = F.Parameters.EnumParameter.MakeChild(enum_t=Endpoint)
    params_ = F.Collections.PointerSet.MakeChild()
    # TODO: Forward this trait to parent
    _is_pickable = fabll.Traits.MakeEdge(F.is_pickable.MakeChild())

    def get_params(self) -> list[fabll.Node]:
        param_tuples = self.params_.get().as_list()
        parameters = [
            F.Collections.PointerTuple.bind_instance(
                param_tuple.instance
            ).deref_pointer()
            for param_tuple in param_tuples
        ]

        return parameters

    def get_param(self, param_name: str) -> "F.Parameters.is_parameter":
        param_tuples = self.params_.get().as_list()
        for param_tuple in param_tuples:
            bound_param_tuple = F.Collections.PointerTuple.bind_instance(
                param_tuple.instance
            )
            (p_name, _) = bound_param_tuple.get_literals_as_list()
            if p_name == param_name:
                return bound_param_tuple.deref_pointer().get_trait(
                    F.Parameters.is_parameter
                )
        raise ValueError(f"Param {param_name} not found")

    @property
    def endpoint(self) -> str:
        return str(self.endpoint_.get().force_extract_literal().get_single())

    @property
    def pick_type(self) -> BoundNode:
        parent_info = self.get_parent()
        if parent_info is None:
            raise Exception("is_pickable_by_type has no parent")
        parent, _ = parent_info
        return not_none(parent.get_type_node())

    @classmethod
    def MakeChild(cls, endpoint: Endpoint, params: dict[str, fabll._ChildField]):
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.AbstractEnums.MakeChild_ConstrainToLiteral(
                [out, cls.endpoint_], endpoint
            )
        )
        for param_name, param_ref in params.items():
            # Create tuple
            param_tuple = F.Collections.PointerTuple.MakeChild()
            out.add_dependant(param_tuple)
            # Add tuple to params_ set
            out.add_dependant(
                F.Collections.PointerSet.MakeEdge(
                    [out, cls.params_],
                    [param_tuple],
                )
            )
            # Add string to tuple
            lit = F.Literals.Strings.MakeChild(param_name)
            out.add_dependant(lit)
            out.add_dependant(
                F.Collections.PointerTuple.AppendLiteral(
                    tup_ref=[param_tuple], elem_ref=[lit]
                )
            )
            # Add param reference to tuple
            out.add_dependant(
                F.Collections.PointerTuple.SetPointer(
                    tup_ref=[param_tuple], elem_ref=[param_ref]
                )
            )
        return out
