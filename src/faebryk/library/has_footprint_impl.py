# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.core import Footprint, LinkNamedParent
from faebryk.library.has_footprint import has_footprint


class has_footprint_impl(has_footprint.impl()):
    @abstractmethod
    def __init__(self) -> None:
        super().__init__()

    def set_footprint(self, fp: Footprint):
        self.get_obj().GIFs.children.connect(
            fp.GIFs.parent, LinkNamedParent.curry("footprint")
        )

    def get_footprint(self) -> Footprint:
        children = self.get_obj().GIFs.children.get_children()
        fps = [c for _, c in children if isinstance(c, Footprint)]
        assert len(fps) == 1, f"candidates: {fps}"
        return fps[0]
