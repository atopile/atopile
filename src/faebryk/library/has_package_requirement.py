# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Sequence

from deprecated import deprecated

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.libs.library import L


@deprecated("Use F.has_package instead")
class has_package_requirement(Module.TraitT.decless()):
    def __init__(self, *package_candidates: str) -> None:
        super().__init__()
        self._package_candidates = list(package_candidates)

    def on_obj_set(self):
        obj = self.get_obj(L.Module)
        obj.add(F.has_package(*self._package_candidates))
        return super().on_obj_set()

    # Delete this
    def get_package_candidates(self) -> Sequence[str]:
        raise NotImplementedError("Use F.has_package instead")
