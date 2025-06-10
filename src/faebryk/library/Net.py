# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from more_itertools import first

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.util import KeyErrorAmbiguous, groupby

logger = logging.getLogger(__name__)


class Net(Module):
    part_of: F.Electrical

    def get_connected_pads(self) -> dict[F.Pad, F.Footprint]:
        """Return a dict of pads connected to this net"""
        return {
            pad: fp
            for mif in self.get_connected_interfaces()
            if (fp := mif.get_parent_of_type(F.Footprint)) is not None
            and (pad := mif.get_parent_of_type(F.Pad)) is not None
        }

    def get_footprints(self) -> set[F.Footprint]:
        return {
            fp
            for mif in self.get_connected_interfaces()
            if (fp := mif.get_parent_of_type(F.Footprint)) is not None
        }

    # TODO should this be here?
    def get_connected_interfaces(self):
        return {
            mif
            for mif in self.part_of.get_connected()
            # TODO: this should be removable since,
            # only mifs of the same type can connect
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
    def find_from_part_of_mif(cls, mif: F.Electrical) -> "Net | None":
        """Return the Net that this "part_of" mif represents"""
        parent = mif.get_parent()
        if parent is None:
            return None
        if isinstance(parent[0], cls):
            return parent[0]
        return None

    @classmethod
    def find_nets_for_mif(cls, mif: F.Electrical) -> set["Net"]:
        """Return all nets that are connected to this mif"""
        return {
            net
            for net_mif in mif.get_connected()
            if (net := cls.find_from_part_of_mif(net_mif))
        }

    @classmethod
    def find_named_net_for_mif(cls, mif: F.Electrical) -> "Net | None":
        nets = cls.find_nets_for_mif(mif)
        named_nets = groupby(
            {n for n in nets if n.has_trait(F.has_overriden_name)},
            lambda n: n.get_trait(F.has_overriden_name).get_name(),
        )
        if len(named_nets) > 1:
            raise KeyErrorAmbiguous(
                list(named_nets),
                "Multiple nets with the same name connected to this mif",
            )
        if not named_nets:
            return None
        same_name_nets = first(named_nets.values())
        if len(same_name_nets) > 1:
            # TODO not sure whether this should be an error
            raise KeyErrorAmbiguous(
                same_name_nets,
                "Multiple nets with the same name connected to this mif",
            )
        return first(same_name_nets)
