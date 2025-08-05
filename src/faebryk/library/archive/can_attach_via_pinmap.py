# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

import faebryk.library._F as F


class can_attach_via_pinmap(F.Footprint.TraitT):
    @abstractmethod
    def attach(self, pinmap: dict[str, F.Electrical | None]): ...
