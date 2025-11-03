# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Callable

import faebryk.core.node as fabll

logger = logging.getLogger(__name__)


class is_optional_defined(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    def __init__(
        self, needed: bool, handle_result: Callable[[bool], None] = lambda _: None
    ):
        self.needed = needed
        self.handle_result = handle_result

    def is_needed(self) -> bool:
        return self.needed

    def _handle_result(self, needed: bool) -> None:
        self.handle_result(needed)
