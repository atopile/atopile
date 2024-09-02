# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class has_footprint_defined(F.has_footprint_impl):
    def __init__(self, fp: F.Footprint) -> None:
        super().__init__()
        self.fp = fp

    def on_obj_set(self):
        self.set_footprint(self.fp)
