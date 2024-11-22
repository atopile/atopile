# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
from pathlib import Path

from faebryk.libs.library import L

logger = logging.getLogger(__name__)


class has_reference_layout(L.Module.TraitT.decless()):
    """
    The module has a reference layout.
    """

    def __init__(self, *paths: os.PathLike):
        self._paths = set(Path(p).expanduser().resolve().absolute() for p in paths)

    @property
    def paths(self) -> set[Path]:
        return self._paths

    def handle_duplicate(self, old: "has_reference_layout", _: L.Node) -> bool:
        old.paths.update(self.paths)
        return False
