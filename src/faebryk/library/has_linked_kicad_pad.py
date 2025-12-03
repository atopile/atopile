# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import ctypes
from typing import Self

import faebryk.core.node as fabll
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.library import _F as F


class has_linked_kicad_pad(fabll.Node):
    """
    A node that has a linked KiCad pad.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    pad_ptr_ = F.Collections.Pointer.MakeChild()
    transformer_ = F.Parameters.StringParameter.MakeChild()

    @property
    def pad(self):
        """Return the KiCad pad associated with this node"""
        return self.pad_ptr_.get().deref()

    def get_transformer(self) -> "PCB_Transformer":
        transformer_id = int(
            self.transformer_.get().force_extract_literal().get_values()[0]
        )
        return ctypes.cast(transformer_id, ctypes.py_object).value

    @classmethod
    def MakeChild(
        cls, pad: fabll._ChildField[fabll.Node], transformer: "PCB_Transformer"
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(pad)
        out.add_dependant(
            F.Collections.Pointer.MakeEdge(
                [out, cls.transformer_], [str(id(transformer))]
            )
        )
        return out
