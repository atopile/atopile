# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import StrEnum
from typing import Any

import faebryk.core.node as fabll
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

    # @property
    # def endpoint(self) -> Endpoint:
    #     return self.endpoint_.get().try_extract_constrained_literal()

    # @property
    # def params(self) -> list[Parameter]:
    #     return self.params_.get().as_list()

    class Endpoint(StrEnum):
        """Query endpoints known to the API."""

        RESISTORS = "resistors"
        CAPACITORS = "capacitors"
        INDUCTORS = "inductors"

    # def __init__(self, endpoint: Endpoint, params: list[Parameter]):
    #     super().__init__()
    #     self.endpoint = endpoint
    #     self._params = params

    # @property
    # def params(self) -> list[Parameter]:
    #     return self._params

    # @property
    # def pick_type(self) -> type[fabll.Module]:
    #     return type(self.get_obj(fabll.Module))

    @classmethod
    def MakeChild(cls, endpoint: str, params: dict[str, fabll.ChildField]):
        out = fabll.ChildField(cls)
        out.add_dependant(
            fabll.ExpressionAliasIs.MakeChild_ToLiteral([out, cls.endpoint_], endpoint)
        )
        for param_name, param_ref in params.items():
            field = fabll.EdgeField(
                [out, cls.params_],
                [param_ref],
                edge=EdgePointer.build(identifier=param_name, order=None),
            )
            out.add_dependant(field)
        return out
