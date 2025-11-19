# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class can_attach_to_footprint_symmetrically(fabll.Node):
    @classmethod
    def __create_type__(
        cls,
        t: fabll.BoundNodeType[fabll.Node, fabll.NodeAttributes],
    ) -> None:
        pass

    # def attach(self, footprint: F.Footprint):
    #     self.obj.add(F.has_footprint_defined(footprint))

    #     for i, j in zip(
    #         footprint.get_children(direct_only=True, types=F.Pad),
    #         self.obj.get_children(direct_only=True, types=F.Electrical),
    #     ):
    #         i.attach(j)
