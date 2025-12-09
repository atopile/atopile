# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import ctypes
from typing import ClassVar, Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.libs.kicad.fileformats import kicad

KiCadPCBFootprint = kicad.pcb.Footprint
KiCadPCBPad = kicad.pcb.Pad
KiCadPCBNet = kicad.pcb.Net


class has_kicad_pcb_footprint(fabll.Node):
    """
    Link applied to:
    - Modules which are represented in the PCB
    - F.KiCadFootprints.is_kicad_footprint nodes which are represented in the PCB
    """

    is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()

    # Registry to prevent garbage collection of Footprint and PCB_Transformer objects.
    # Store objects by their id() so ctypes.cast can retrieve them later.
    _footprint_registry: ClassVar[dict[int, KiCadPCBFootprint]] = {}
    _transformer_registry: ClassVar[dict[int, "PCB_Transformer"]] = {}

    footprint_ = F.Parameters.StringParameter.MakeChild()
    transformer_ = F.Parameters.StringParameter.MakeChild()

    @classmethod
    def MakeChild(
        cls, footprint: KiCadPCBFootprint, transformer: PCB_Transformer
    ) -> fabll._ChildField[Self]:
        # Store objects in registries to prevent garbage collection.
        cls._footprint_registry[id(footprint)] = footprint
        cls._transformer_registry[id(transformer)] = transformer

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

    def setup(self, footprint: KiCadPCBFootprint, transformer: PCB_Transformer) -> Self:
        # Store objects in registries to prevent garbage collection.
        self._footprint_registry[id(footprint)] = footprint
        self._transformer_registry[id(transformer)] = transformer

        self.footprint_.get().alias_to_single(value=str(id(footprint)))
        self.transformer_.get().alias_to_single(value=str(id(transformer)))
        return self

    def get_fp(self) -> KiCadPCBFootprint:
        footprint_id = int(
            self.footprint_.get().force_extract_literal().get_values()[0]
        )
        return ctypes.cast(footprint_id, ctypes.py_object).value

    def get_transformer(self) -> "PCB_Transformer":
        transformer_id = int(
            self.transformer_.get().force_extract_literal().get_values()[0]
        )
        return ctypes.cast(transformer_id, ctypes.py_object).value


class has_kicad_pcb_pad(fabll.Node):
    is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()

    # Registry to prevent garbage collection of Footprint and PCB_Transformer objects.
    # Store objects by their id() so ctypes.cast can retrieve them later.
    _footprint_registry: ClassVar[dict[int, KiCadPCBFootprint]] = {}
    _transformer_registry: ClassVar[dict[int, "PCB_Transformer"]] = {}
    _pad_registry: ClassVar[dict[int, list[KiCadPCBPad]]] = {}

    footprint_ = F.Parameters.StringParameter.MakeChild()
    pad_ = F.Parameters.StringParameter.MakeChild()
    transformer_ = F.Parameters.StringParameter.MakeChild()

    @classmethod
    def MakeChild(
        cls,
        footprint: KiCadPCBFootprint,
        pad: list[KiCadPCBPad],
        transformer: "PCB_Transformer",
    ) -> fabll._ChildField[Self]:
        # Store objects in registries to prevent garbage collection.
        cls._footprint_registry[id(footprint)] = footprint
        cls._pad_registry[id(pad)] = pad
        cls._transformer_registry[id(transformer)] = transformer

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
        footprint: "KiCadPCBFootprint",
        pads: list[KiCadPCBPad],
        transformer: "PCB_Transformer",
    ) -> Self:
        # Store objects in registries to prevent garbage collection.
        self._footprint_registry[id(footprint)] = footprint
        self._pad_registry[id(pads)] = pads
        self._transformer_registry[id(transformer)] = transformer

        self.footprint_.get().alias_to_single(value=str(id(footprint)))
        self.transformer_.get().alias_to_single(value=str(id(transformer)))
        self.pad_.get().alias_to_single(value=str(id(pads)))
        return self

    def get_pads(self) -> tuple[KiCadPCBFootprint, list[KiCadPCBPad]]:
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


class has_kicad_pcb_net(fabll.Node):
    is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()

    # Registry to prevent garbage collection of Footprint and PCB_Transformer objects.
    # Store objects by their id() so ctypes.cast can retrieve them later.
    _transformer_registry: ClassVar[dict[int, "PCB_Transformer"]] = {}
    _net_registry: ClassVar[dict[int, "KiCadPCBNet"]] = {}

    net_ = F.Parameters.StringParameter.MakeChild()
    transformer_ = F.Parameters.StringParameter.MakeChild()

    @classmethod
    def MakeChild(
        cls, net: "KiCadPCBNet", transformer: "PCB_Transformer"
    ) -> fabll._ChildField[Self]:
        # Store objects in registries to prevent garbage collection.
        cls._net_registry[id(net)] = net
        cls._transformer_registry[id(transformer)] = transformer

        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Collections.Pointer.MakeEdge([out, cls.net_], [str(id(net))])
        )
        out.add_dependant(
            F.Collections.Pointer.MakeEdge(
                [out, cls.transformer_], [str(id(transformer))]
            )
        )
        return out

    def setup(self, net: "KiCadPCBNet", transformer: "PCB_Transformer") -> Self:
        # Store objects in registries to prevent garbage collection.
        self._net_registry[id(net)] = net
        self._transformer_registry[id(transformer)] = transformer

        self.net_.get().alias_to_single(value=str(id(net)))
        self.transformer_.get().alias_to_single(value=str(id(transformer)))
        return self

    def get_net(self) -> KiCadPCBNet:
        net_id = int(self.net_.get().force_extract_literal().get_values()[0])
        return ctypes.cast(net_id, ctypes.py_object).value

    def get_transformer(self) -> "PCB_Transformer":
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
    footprint = pcb.kicad_pcb.footprints[1]  # return 2nd fp in the PCB file
    module = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)

    return g, tg, app, transformer, footprint, module, kpcb


def test_has_kicad_pcb_footprint_trait():
    _, _, _, transformer, footprint, module, _ = setup_pcb_transformer_test()

    fabll.Traits.create_and_add_instance_to(
        node=module, trait=has_kicad_pcb_footprint
    ).setup(footprint, transformer)

    trait = module.try_get_trait(has_kicad_pcb_footprint)
    assert trait is not None
    assert trait.get_transformer() is transformer
    kicad_pcb_fp = trait.get_fp()
    assert kicad_pcb_fp is footprint

    assert kicad_pcb_fp.name == footprint.name
    assert kicad_pcb_fp.name == "lcsc:LED0603-RD-YELLOW"


def test_has_kicad_pcb_pad_trait():
    _, _, _, transformer, footprint, module, _ = setup_pcb_transformer_test()

    pads = footprint.pads

    fabll.Traits.create_and_add_instance_to(node=module, trait=has_kicad_pcb_pad).setup(
        footprint, pads, transformer
    )

    trait = module.try_get_trait(has_kicad_pcb_pad)
    assert trait is not None
    assert trait.get_transformer() is transformer
    retrieved_footprint, retrieved_pads = trait.get_pads()

    assert retrieved_footprint is footprint

    assert len(retrieved_pads) == len(pads)
    for retrieved_pad, pad in zip(retrieved_pads, pads):
        assert retrieved_pad.name == pad.name


def test_has_kicad_pcb_net_trait():
    _, _, _, transformer, _, module, kpcb = setup_pcb_transformer_test()

    net = kpcb.nets

    fabll.Traits.create_and_add_instance_to(node=module, trait=has_kicad_pcb_net).setup(
        net[0], transformer
    )

    trait = module.try_get_trait(has_kicad_pcb_net)
    assert trait is not None
    assert trait.get_transformer() is transformer
    retrieved_net = trait.get_net()
    assert retrieved_net.name == net[0].name
    assert retrieved_net.number == net[0].number
