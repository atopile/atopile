# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import StrEnum

import faebryk.core.node as fabll
import faebryk.library._F as F


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
        return parameters  # type: ignore

    def get_param(self, param_name: str) -> fabll.Node:
        param_tuples = self.params_.get().as_list()
        for param_tuple in param_tuples:
            if (
                F.Collections.PointerTuple.bind_instance(
                    param_tuple.instance
                ).get_literals_as_list()[0]
                == param_name
            ):
                return F.Collections.PointerTuple.bind_instance(
                    param_tuple.instance
                ).deref_pointer()  # type: ignore
        raise ValueError(f"Param {param_name} not found")

    @property
    def endpoint(self) -> str:
        return str(self.endpoint_.get().force_extract_literal().get_values()[0])

    @property  # TODO: make this return Resistor Class
    def pick_type(self):  # -> type[fabll.Node]:
        parent = self.get_parent()
        if parent is None:
            raise Exception("is_pickable_by_type has no parent")
        return parent[0]

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
