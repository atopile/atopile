# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class has_footprint_impl(F.has_footprint.impl()):
    def set_footprint(self, fp: F.Footprint):
        self.obj.add(fp, name="footprint")

    def get_footprint(self) -> F.Footprint:
        fps = self.obj.get_children(direct_only=True, types=F.Footprint)
        assert len(fps) == 1, f"In obj: {self.obj}: candidates: {fps}"
        return next(iter(fps))
