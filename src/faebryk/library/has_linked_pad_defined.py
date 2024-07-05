# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from faebryk.library.has_linked_pad import has_linked_pad
from faebryk.library.Pad import Pad


class has_linked_pad_defined(has_linked_pad.impl()):
    def __init__(self, pad: Pad) -> None:
        super().__init__()
        self.pad = pad

    def get_pad(self) -> Pad:
        return self.pad
