# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import StrEnum

import faebryk.library._F as F
import faebryk.libs.library.L as L
from faebryk.core.parameter import Parameter


class is_pickable_by_type(F.is_pickable.decless()):
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

    def __init__(self, endpoint: Endpoint, params: list[Parameter]):
        super().__init__()
        self.endpoint = endpoint
        self._params = params

    @property
    def params(self) -> list[Parameter]:
        return self._params

    @property
    def pick_type(self) -> type[L.Module]:
        return type(self.get_obj(L.Module))
