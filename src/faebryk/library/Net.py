# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module

logger = logging.getLogger(__name__)


class Net(Module):
    part_of: F.Electrical

    def get_fps(self):
        return {
            pad: fp
            for mif in self.get_connected_interfaces()
            if (fp := mif.get_parent_of_type(F.Footprint)) is not None
            and (pad := mif.get_parent_of_type(F.Pad)) is not None
        }

    # TODO should this be here?
    def get_connected_interfaces(self):
        return {
            mif
            for mif in self.part_of.get_connected()
            if isinstance(mif, type(self.part_of))
        }

    def __repr__(self) -> str:
        up = super().__repr__()
        if self.has_trait(F.has_overriden_name):
            return f"{up}'{self.get_trait(F.has_overriden_name).get_name()}'"
        else:
            return up

    @classmethod
    def with_name(cls, name: str) -> "Net":
        n = cls()
        n.add(F.has_overriden_name_defined(name))
        return n

    @classmethod
    def from_part_of_mif(cls, mif: F.Electrical) -> "Net | None":
        parent = mif.get_parent()
        if parent is None:
            return None
        if isinstance(parent[0], cls):
            return parent[0]
        return None
