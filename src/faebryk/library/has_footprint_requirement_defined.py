# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import Sequence

import faebryk.library._F as F

logger = logging.getLogger(__name__)


class has_footprint_requirement_defined(F.has_footprint_requirement.impl()):
    def __init__(
        self, req: Sequence[tuple[str, int | None]] = None, footprint: str = None
    ) -> None:
        super().__init__()
        self.req = req or []
        if footprint is not None:
            self.req.append((footprint, None))

    def get_footprint_requirement(self) -> Sequence[tuple[str, int | None]]:
        return self.req
