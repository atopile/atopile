# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Callable

from faebryk.library.is_optional import is_optional

logger = logging.getLogger(__name__)


class is_optional_defined(is_optional.impl()):
    def __init__(
        self, needed: bool, handle_result: Callable[[bool], None] = lambda _: None
    ):
        self.needed = needed
        self.handle_result = handle_result
        super().__init__()

    def is_needed(self) -> bool:
        return self.needed

    def _handle_result(self, needed: bool) -> None:
        self.handle_result(needed)
