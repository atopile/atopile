# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from typing import TYPE_CHECKING

import faebryk.library._F as F

if TYPE_CHECKING:
    from faebryk.library.Pad import Pad


class has_linked_pad_defined(F.has_linked_pad.impl()):
    def __init__(self, pad: "Pad") -> None:
        super().__init__()
        self.pad = pad

    def get_pad(self) -> "Pad":
        return self.pad
