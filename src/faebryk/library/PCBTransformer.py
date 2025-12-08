# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import ctypes
from typing import Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.libs.kicad.fileformats import kicad

KiCadPCB = kicad.pcb.KicadPcb
KiCadFootprint = kicad.pcb.Footprint
KiCadPad = kicad.pcb.Pad
KiCadNet = kicad.pcb.Net


class has_linked_kicad_footprint(fabll.Node):
    """
    Link applied to:
    - Modules which are represented in the PCB
    - F.Footprints.Footprint which are represented in the PCB
    """

    _is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()

    footprint_ = F.Parameters.StringParameter.MakeChild()
    transformer_ = F.Parameters.StringParameter.MakeChild()

    @classmethod
    def MakeChild(
        cls, footprint: "KiCadFootprint", transformer: "PCB_Transformer"
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Collections.Pointer.MakeEdge([out, cls.footprint_], [str(id(footprint))])
        )
        out.add_dependant(
            F.Collections.Pointer.MakeEdge(
                [out, cls.transformer_], [str(id(transformer))]
            )
        )
        return out

    def setup(
        self, footprint: "KiCadFootprint", transformer: "PCB_Transformer"
    ) -> Self:
        self.footprint_.get().alias_to_single(value=str(id(footprint)))
        self.transformer_.get().alias_to_single(value=str(id(transformer)))
        return self

    def get_fp(self) -> KiCadFootprint:
        footprint_id = int(
            self.footprint_.get().force_extract_literal().get_values()[0]
        )
        return ctypes.cast(footprint_id, ctypes.py_object).value

    def get_transformer(self) -> "PCB_Transformer":
        transformer_id = int(
            self.transformer_.get().force_extract_literal().get_values()[0]
        )
        return ctypes.cast(transformer_id, ctypes.py_object).value


class has_linked_kicad_pad(fabll.Node):
    _is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()

    footprint_ = F.Parameters.StringParameter.MakeChild()
    pad_ = F.Parameters.StringParameter.MakeChild()
    transformer_ = F.Parameters.StringParameter.MakeChild()

    @classmethod
    def MakeChild(
        cls,
        footprint: "KiCadFootprint",
        pad: list["KiCadPad"],
        transformer: "PCB_Transformer",
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Collections.Pointer.MakeEdge([out, cls.footprint_], [str(id(footprint))])
        )
        out.add_dependant(
            F.Collections.Pointer.MakeEdge([out, cls.pad_], [str(id(pad))])
        )
        out.add_dependant(
            F.Collections.Pointer.MakeEdge(
                [out, cls.transformer_], [str(id(transformer))]
            )
        )
        return out

    def setup(
        self,
        footprint: "KiCadFootprint",
        pads: list[KiCadPad],
        transformer: "PCB_Transformer",
    ) -> Self:
        self.footprint_.get().alias_to_single(value=str(id(footprint)))
        self.transformer_.get().alias_to_single(value=str(id(transformer)))
        self.pad_.get().alias_to_single(value=str(id(pads)))
        return self

    def get_pads(self) -> tuple[KiCadFootprint, list[KiCadPad]]:
        footprint_id = int(
            self.footprint_.get().force_extract_literal().get_values()[0]
        )
        pad_id = int(self.pad_.get().force_extract_literal().get_values()[0])
        return (
            ctypes.cast(footprint_id, ctypes.py_object).value,
            ctypes.cast(pad_id, ctypes.py_object).value,
        )

    def get_transformer(self) -> "PCB_Transformer":
        transformer_id = int(
            self.transformer_.get().force_extract_literal().get_values()[0]
        )
        return ctypes.cast(transformer_id, ctypes.py_object).value
        transformer_id = int(
            self.transformer_.get().force_extract_literal().get_values()[0]
        )
        return ctypes.cast(transformer_id, ctypes.py_object).value

def setup_pcb_transformer_test():
    from faebryk.libs.test.fileformats import PCBFILE

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    pcb = kicad.loads(kicad.pcb.PcbFile, PCBFILE)
    kpcb = pcb.kicad_pcb
    app = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)
    transformer = PCB_Transformer(pcb=kpcb, app=app)
    footprint = pcb.kicad_pcb.footprints[0]
    module = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)

    return g, tg, app, transformer, footprint, module, kpcb


def test_pcb_transformer_traits():
    _, _, app, transformer, _, _, kpcb = setup_pcb_transformer_test()

    # TODO: assert transformer.tg is app.tg
    assert transformer.app is app
    assert transformer.pcb is kpcb

