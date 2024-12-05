# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Sequence

from faebryk.core.module import Module


class has_footprint_requirement(Module.TraitT.decless()):
    def __init__(self, *footprint_candidates: str) -> None:
        super().__init__()
        self.footprint_candidates = list(footprint_candidates)

    def get_footprint_candidates(self) -> Sequence[str]:
        return self.footprint_candidates
