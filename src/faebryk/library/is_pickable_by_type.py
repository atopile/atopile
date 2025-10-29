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
    params_ = fabll.ChildField(fabll.Node)  # TODO: change to list
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    class Endpoint(StrEnum):
        """Query endpoints known to the API."""

        RESISTORS = "resistors"
        CAPACITORS = "capacitors"
        INDUCTORS = "inductors"

    # @property
    # def endpoint(self) -> Endpoint:
    #     return self.endpoint_.get().try_extract_constrained_literal()

    @property
    def params(self) -> list[fabll.Parameter]:
        parameters: list[fabll.Parameter] = []
        EdgePointer.visit_pointed_edges(
            bound_node=self.params_.get().instance,
            ctx=parameters,
            f=lambda ctx, edge: ctx.append(
                fabll.Parameter.bind_instance(edge.g().bind(node=edge.edge().target()))
            ),
        )
        return parameters

    @property
    def endpoint(self) -> str:
        return str(self.endpoint_.get().try_extract_constrained_literal())

    @property
    def pick_type(self) -> type[fabll.Node]:
        return self.__class__

    @classmethod
    def MakeChild(cls, endpoint: str, params: dict[str, fabll.ChildField]):
        out = fabll.ChildField(cls)
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral(
                [out, cls.endpoint_], endpoint
            )
        )
        for param_name, param_ref in params.items():
            field = fabll.EdgeField(
                [out, cls.params_],
                [param_ref],
                edge=EdgePointer.build(identifier=param_name, order=None),
            )
            out.add_dependant(field)
        return out
