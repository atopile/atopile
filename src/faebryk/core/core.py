# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Any, Callable

from typing_extensions import Self

from faebryk.libs.util import ConfigFlag

logger = logging.getLogger(__name__)

ID_REPR = ConfigFlag("ID_REPR", False, "Add object id to repr")


class FaebrykLibObject:
    def __init__(self) -> None: ...

    def builder(self, op: Callable[[Self], Any]) -> Self:
        op(self)
        return self


class Namespace:
    """Marker class for namespace objects."""

    pass
