# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from more_itertools import first

import faebryk.library._F as F
from faebryk.libs.util import not_none


class has_footprint_impl(F.has_footprint.impl()):
    def set_footprint(self, fp: F.Footprint):
        self.obj.add(fp, name="footprint")

    def try_get_footprint(self) -> F.Footprint | None:
        if fps := self.obj.get_children(direct_only=True, types=F.Footprint):
            assert len(fps) == 1, f"In obj: {self.obj}: candidates: {fps}"
            return first(fps)
        else:
            return None

    def get_footprint(self) -> F.Footprint:
        return not_none(self.try_get_footprint())
