# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import StrEnum

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.zig.gen.faebryk.pointer import EdgePointer


class is_pickable_by_type(fabll.Node):
    """
    Marks a module as being parametrically selectable using the given parameters.

    Must map to an existing API endpoint.

    Should be named "pickable" to aid overriding by subclasses.
    """

    endpoint_ = fabll.ChildField(fabll.Parameter)
    params_ = F.Collections.PointerSet.MakeChild()
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    # TODO: Forward this trait to parent
    _is_pickable = fabll.ChildField(F.is_pickable)

    class Endpoint(StrEnum):
        """Query endpoints known to the API."""

        RESISTORS = "resistors"
        CAPACITORS = "capacitors"
        INDUCTORS = "inductors"

    @property
    def params(self) -> list[fabll.Parameter]:
        param_tuples = self.params_.get().as_list()
        parameters = [
            F.Collections.PointerTuple.bind_instance(
                param_tuple.instance
            ).deref_pointer()
            for param_tuple in param_tuples
        ]
        return parameters  # type: ignore

    def get_param(self, param_name: str) -> fabll.Parameter:
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
        return str(self.endpoint_.get().try_extract_constrained_literal())

    @property  # TODO: make this return Resistor Class
    def pick_type(self):  # -> type[fabll.Node]:
        parent = self.get_parent()
        if parent is None:
            raise Exception("is_pickable_by_type has no parent")
        return parent[0]

    @classmethod
    def MakeChild(cls, endpoint: Endpoint, params: dict[str, fabll.ChildField]):
        out = fabll.ChildField(cls)
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral(
                [out, cls.endpoint_], endpoint
            )
        )
        for param_name, param_ref in params.items():
            # Create tuple
            param_tuple = F.Collections.PointerTuple.MakeChild()
            out.add_dependant(param_tuple)
            # Add tuple to params_ set
            out.add_dependant(
                F.Collections.PointerSet.EdgeField(
                    [out, cls.params_],
                    [param_tuple],
                )
            )
            # Add string to tuple
            lit = fabll.LiteralNode.MakeChild(value=param_name)
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
