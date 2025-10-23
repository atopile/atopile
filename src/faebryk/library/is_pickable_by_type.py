# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import StrEnum
from typing import Any

import faebryk.core.node as fabll


class is_pickable_by_type(fabll.Node):
    """
    Marks a module as being parametrically selectable using the given parameters.

    Must map to an existing API endpoint.

    Should be named "pickable" to aid overriding by subclasses.
    """

    @classmethod
    def __create_type__(cls, t: fabll.BoundNodeType[fabll.Node, Any]) -> None:
        cls.endpoint_ = t.Child(nodetype=fabll.Parameter)
        cls.params_ = t.Child(nodetype=fabll.Node)  # TODO: change to list

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
