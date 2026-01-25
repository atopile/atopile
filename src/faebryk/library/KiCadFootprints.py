# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import ctypes
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.kicad.fileformats import kicad

if TYPE_CHECKING:
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer

KiCadPCBFootprint = kicad.pcb.Footprint
KiCadPCBPad = kicad.pcb.Pad
KiCadPCBNet = kicad.pcb.Net


class has_associated_kicad_pcb_footprint(fabll.Node):
    """
    Link applied to:
    - Modules which are represented in the PCB
    - has_associated_kicad_pcb_footprint nodes which are represented in the PCB
    """

    is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()

    # Registry to prevent garbage collection of Footprint and PCB_Transformer objects.
    # Store objects by their id() so ctypes.cast can retrieve them later.
    _footprint_registry: ClassVar[dict[int, KiCadPCBFootprint]] = {}
    _transformer_registry: ClassVar[dict[int, "PCB_Transformer"]] = {}

    footprint_ = F.Parameters.StringParameter.MakeChild()
    transformer_ = F.Parameters.StringParameter.MakeChild()
    kicad_identifier_ = F.Parameters.StringParameter.MakeChild()
    library_name_ = F.Parameters.StringParameter.MakeChild()

    @classmethod
    def MakeChild(
        cls, footprint: KiCadPCBFootprint, transformer: "PCB_Transformer"
    ) -> fabll._ChildField[Self]:
        # Store objects in registries to prevent garbage collection.
        cls._footprint_registry[id(footprint)] = footprint
        cls._transformer_registry[id(transformer)] = transformer

        kicad_identifier = footprint.name
        library_name = footprint.name.split(":")[0]

        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_SetSuperset(
                [out, cls.kicad_identifier_], kicad_identifier
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_SetSuperset(
                [out, cls.library_name_], library_name
            )
        )
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
        self, footprint: KiCadPCBFootprint, transformer: "PCB_Transformer"
    ) -> Self:
        # Store objects in registries to prevent garbage collection.
        self._footprint_registry[id(footprint)] = footprint
        self._transformer_registry[id(transformer)] = transformer

        self.footprint_.get().set_singleton(value=str(id(footprint)))
        self.transformer_.get().set_singleton(value=str(id(transformer)))

        kicad_identifier = footprint.name
        library_name = footprint.name.split(":")[0]
        self.kicad_identifier_.get().set_singleton(value=kicad_identifier)
        self.library_name_.get().set_singleton(value=library_name)
        return self

    def get_footprint(self) -> KiCadPCBFootprint:
        footprint_id = int(self.footprint_.get().extract_singleton())
        return ctypes.cast(footprint_id, ctypes.py_object).value

    def get_transformer(self) -> "PCB_Transformer":
        transformer_id = int(self.transformer_.get().extract_singleton())
        return ctypes.cast(transformer_id, ctypes.py_object).value

    def get_kicad_identifier(self) -> str:
        return self.kicad_identifier_.get().extract_singleton()

    def get_library_name(self) -> str:
        return self.library_name_.get().extract_singleton()


class has_associated_kicad_pcb_pad(fabll.Node):
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

        self.footprint_.get().set_singleton(value=str(id(footprint)))
        self.transformer_.get().set_singleton(value=str(id(transformer)))
        self.pad_.get().set_singleton(value=str(id(pads)))
        return self

    def get_pads(self) -> tuple[KiCadPCBFootprint, list[KiCadPCBPad]]:
        footprint_id = int(self.footprint_.get().extract_singleton())
        pad_id = int(self.pad_.get().extract_singleton())
        return (
            ctypes.cast(footprint_id, ctypes.py_object).value,
            ctypes.cast(pad_id, ctypes.py_object).value,
        )

    def get_pad(self) -> KiCadPCBPad:
        pad_id = int(self.pad_.get().extract_singleton())
        return ctypes.cast(pad_id, ctypes.py_object).value[0]

    def get_transformer(self) -> "PCB_Transformer":
        transformer_id = int(self.transformer_.get().extract_singleton())
        return ctypes.cast(transformer_id, ctypes.py_object).value


class has_associated_kicad_pcb_net(fabll.Node):
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

        self.net_.get().set_singleton(value=str(id(net)))
        self.transformer_.get().set_singleton(value=str(id(transformer)))
        return self

    def get_net(self) -> KiCadPCBNet:
        net_id = int(self.net_.get().extract_singleton())
        return ctypes.cast(net_id, ctypes.py_object).value

    def get_transformer(self) -> "PCB_Transformer":
        transformer_id = int(self.transformer_.get().extract_singleton())
        return ctypes.cast(transformer_id, ctypes.py_object).value


class has_associated_kicad_library_footprint(fabll.Node):
    """
    Associate a footprint with a KiCad library footprint file.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()
    kicad_footprint_file_path_ = F.Parameters.StringParameter.MakeChild()
    pad_names_ = F.Collections.PointerSequence.MakeChild()
    kicad_identifier_ = F.Parameters.StringParameter.MakeChild()
    library_name_ = F.Parameters.StringParameter.MakeChild()

    def get_library_name(self) -> str:
        lit = self.library_name_.get().try_extract_singleton()
        if lit is not None:
            return lit
        return Path(self.get_kicad_footprint_file_path()).parent.name

    def get_kicad_identifier(self) -> str:
        lit = self.kicad_identifier_.get().try_extract_singleton()
        if lit is not None:
            return lit
        return (
            f"{self.get_library_name()}:"
            f"{Path(self.get_kicad_footprint_file_path()).stem}"
        )

    def get_kicad_footprint_file_path(self) -> str:
        """
        Get the KiCad footprint file path.

        For LCSC-picked parts, this is set directly via setup().
        For atomic parts, is_atomic_part.get_kicad_library_footprint() must be
        called first to lazily set up this value.
        """
        param = self.kicad_footprint_file_path_.get()

        if lit := param.try_extract_singleton():
            return lit

        raise ValueError(
            "kicad_footprint_file_path not set. "
            "For atomic parts, call is_atomic_part.get_kicad_library_footprint() first."
        )

    def get_pad_names(self) -> list[str]:
        """Pad names sorted alphabetically"""
        return sorted(
            [
                lit.cast(F.Literals.Strings).get_single()
                for lit in self.pad_names_.get().as_list()
            ]
        )

    @staticmethod
    def _extract_pad_names_from_kicad_footprint_file(
        kicad_footprint_file: "kicad.footprint.FootprintFile",
    ) -> list[str]:
        """
        Extract the pad names from a KiCad footprint file if the pad is on
        a copper layer
        """

        return [
            pad.name
            for pad in kicad_footprint_file.footprint.pads
            if any("Cu" in layer for layer in pad.layers)
        ]

    @staticmethod
    def _create_kicad_identifier(
        kicad_footprint_file: "kicad.footprint.FootprintFile",
        library_name: str | None,
        kicad_footprint_file_path: str | None = None,
    ) -> tuple[str, str]:
        if ":" in kicad_footprint_file.footprint.name:
            fp_lib_name = kicad_footprint_file.footprint.name.split(":")[0]
            if library_name is not None and library_name != fp_lib_name:
                raise ValueError(
                    f"lib_name must be empty or same as fp lib name, if fp has libname:"
                    f" fp_lib_name: {fp_lib_name}, library_name: {library_name}"
                )
            library_name = fp_lib_name
        else:
            if library_name is None:
                if kicad_footprint_file_path is not None:
                    library_name = Path(kicad_footprint_file_path).parent.name
                else:
                    raise ValueError(
                        "lib_name must be specified if fp has no lib prefix: "
                        f"{kicad_footprint_file.footprint.name}"
                    )
        assert library_name is not None
        return (
            f"{library_name}:{kicad.fp_get_base_name(kicad_footprint_file.footprint)}",
            library_name,
        )

    @classmethod
    def MakeChild(  # type: ignore[override]
        cls, library_name: str | None, kicad_footprint_file_path: str
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        fp_path = Path(kicad_footprint_file_path)

        out.add_dependant(
            F.Literals.Strings.MakeChild_SetSuperset(
                [out, cls.kicad_footprint_file_path_], kicad_footprint_file_path
            )
        )

        # Read file to extract pad names and create kicad_identifier
        fp_file = kicad.loads(kicad.footprint.FootprintFile, fp_path)
        kicad_identifier, lib_name = cls._create_kicad_identifier(
            fp_file, library_name, kicad_footprint_file_path
        )

        out.add_dependant(
            F.Literals.Strings.MakeChild_SetSuperset(
                [out, cls.kicad_identifier_], kicad_identifier
            )
        )
        pad_names = cls._extract_pad_names_from_kicad_footprint_file(fp_file)
        out.add_dependant(
            F.Literals.Strings.MakeChild_SetSuperset([out, cls.pad_names_], *pad_names)
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_SetSuperset([out, cls.library_name_], lib_name)
        )
        return out

    def setup(
        self,
        kicad_footprint_file_path: str,
        library_name: str | None,
    ) -> Self:
        fp_path = Path(kicad_footprint_file_path)
        self.kicad_footprint_file_path_.get().set_superset(kicad_footprint_file_path)

        fp_file = kicad.loads(kicad.footprint.FootprintFile, fp_path)
        pad_names = self._extract_pad_names_from_kicad_footprint_file(fp_file)
        pad_name_lits = [
            F.Literals.Strings.bind_typegraph_from_instance(instance=self.instance)
            .create_instance(g=self.instance.g())
            .setup_from_values(name)
            for name in pad_names
        ]
        self.pad_names_.get().append(*pad_name_lits)
        kicad_identifier, lib_name = self._create_kicad_identifier(
            fp_file, library_name, kicad_footprint_file_path
        )
        self.kicad_identifier_.get().set_superset(kicad_identifier)
        self.library_name_.get().set_superset(lib_name)
        return self


def setup_pcb_transformer_test():
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
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
        node=module, trait=has_associated_kicad_pcb_footprint
    ).setup(footprint, transformer)

    trait = module.try_get_trait(has_associated_kicad_pcb_footprint)
    assert trait is not None
    assert trait.get_transformer() is transformer
    kicad_pcb_fp = trait.get_footprint()
    assert kicad_pcb_fp is footprint

    assert kicad_pcb_fp.name == footprint.name
    assert kicad_pcb_fp.name == "lcsc:LED0603-RD-YELLOW"
    assert trait.get_kicad_identifier() == footprint.name == "lcsc:LED0603-RD-YELLOW"
    assert trait.get_library_name() == footprint.name.split(":")[0] == "lcsc"


def test_has_kicad_pcb_pad_trait():
    _, _, _, transformer, footprint, module, _ = setup_pcb_transformer_test()

    pads = footprint.pads

    fabll.Traits.create_and_add_instance_to(
        node=module, trait=has_associated_kicad_pcb_pad
    ).setup(footprint, pads, transformer)

    trait = module.try_get_trait(has_associated_kicad_pcb_pad)
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

    fabll.Traits.create_and_add_instance_to(
        node=module, trait=has_associated_kicad_pcb_net
    ).setup(net[0], transformer)

    trait = module.try_get_trait(has_associated_kicad_pcb_net)
    assert trait is not None
    assert trait.get_transformer() is transformer
    retrieved_net = trait.get_net()
    assert retrieved_net.name == net[0].name
    assert retrieved_net.number == net[0].number


def test_has_associated_kicad_library_footprint():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _NodeWithAssociatedFootprint(fabll.Node):
        """User defined node that can attach to a footprint"""

        is_module_ = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        can_attach_to_footprint_ = fabll.Traits.MakeEdge(
            F.Footprints.can_attach_to_footprint.MakeChild()
        )

    user_node = _NodeWithAssociatedFootprint.bind_typegraph(tg).create_instance(g=g)

    # create footprint from kicad footprint file
    # node with is_kicad_footprint and is_generated_by_kicad_footprint traits
    # node with is_footprint trait, linked to the kicad footprint node by the
    #   has_linked_kicad_footprint trait getting a child of type is_kicad_footprint
    # user_node will get the has_associated_footprint trait which links to the
    # is_footprint trait
    from src.faebryk.libs.test.fileformats import FPFILE  # random SMD LED footprint

    fp_file = kicad.loads(kicad.footprint.FootprintFile, FPFILE)

    # TODO: generate footprint and kicad footprint nodes

    fabll.Traits.create_and_add_instance_to(
        node=user_node, trait=has_associated_kicad_library_footprint
    ).setup(kicad_footprint_file_path=str(FPFILE), library_name="smol_part_lib")

    assert user_node.has_trait(has_associated_kicad_library_footprint)

    gen_kfp_trait = user_node.get_trait(has_associated_kicad_library_footprint)
    fp_names = has_associated_kicad_library_footprint._extract_pad_names_from_kicad_footprint_file(  # noqa: E501
        fp_file
    )

    assert gen_kfp_trait.get_kicad_identifier() == "smol_part_lib:LED_0201_0603Metric"
    assert gen_kfp_trait.get_library_name() == "smol_part_lib"
    assert gen_kfp_trait.get_kicad_footprint_file_path() == str(FPFILE)
    assert gen_kfp_trait.get_pad_names() == fp_names
