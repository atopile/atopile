# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import ctypes
from typing import Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.library import _F as F


class has_linked_kicad_footprint(fabll.Node):
    """
    A node that has a linked KiCad footprint.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    footprint_ptr_ = F.Collections.Pointer.MakeChild()
    transformer_ = F.Parameters.StringParameter.MakeChild()

    @property
    def footprint(self):
        """Return the KiCad footprint associated with this node"""
        return self.footprint_ptr_.get().deref()

    def get_transformer(self) -> "PCB_Transformer":
        transformer_id = int(
            self.transformer_.get().force_extract_literal().get_values()[0]
        )
        return ctypes.cast(transformer_id, ctypes.py_object).value

    def set_footprint(self, footprint: fabll.Node):
        # TODO
        pass

    @classmethod
    def MakeChild(
        cls, footprint: fabll._ChildField[fabll.Node], transformer: "PCB_Transformer"
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(footprint)
        out.add_dependant(
            F.Collections.Pointer.MakeEdge([out, cls.footprint_ptr_], [footprint])
        )
        out.add_dependant(
            F.Collections.Pointer.MakeEdge(
                [out, cls.transformer_], [str(id(transformer))]
            )
        )
        return out


def test_has_linked_kicad_footprint():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class TestKiCadFootprint(fabll.Node):
        _is_kicad_footprint = fabll.Traits.MakeEdge(F.is_kicad_footprint.MakeChild())

    class TestFootprint(fabll.Node):
        _is_footprint = fabll.Traits.MakeEdge(F.Footprints.is_footprint.MakeChild())
        _has_linked_kicad_footprint = fabll.Traits.MakeEdge(
            has_linked_kicad_footprint.MakeChild(
                TestKiCadFootprint.MakeChild(), transformer=None
            )
        )
        pads_ = F.Collections.PointerSet.MakeChild()  # TODO

    fp = TestFootprint.bind_typegraph(tg=tg).create_instance(g=g)
    assert fp.has_trait(has_linked_kicad_footprint)
    kicad_fp = fp.get_trait(has_linked_kicad_footprint).footprint
    assert kicad_fp.has_trait(F.is_kicad_footprint)
