# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import ctypes
from pathlib import Path
from typing import Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
from faebryk.library import _F as F
from faebryk.library.PCBTransformer import PCB_Transformer
from faebryk.libs.kicad.fileformats import kicad


class is_kicad_pad(fabll.Node):
    """
    A node that is a KiCad pad.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()
    pad_name_ = F.Parameters.StringParameter.MakeChild()

    def get_pad_name(self) -> str:
        return self.pad_name_.get().force_extract_literal().get_values()[0]

    @classmethod
    def MakeChild(cls, pad_name: str) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.pad_name_], pad_name
            )
        )
        return out


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


class is_kicad_footprint(fabll.Node):
    """
    Marks a node as a KiCad footprint.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()
    kicad_identifier_ = F.Parameters.StringParameter.MakeChild()

    def get_kicad_footprint_identifier(self) -> str:
        return self.kicad_identifier_.get().force_extract_literal().get_values()[0]

    def get_kicad_footprint_name(self) -> str:
        return self.get_kicad_footprint_identifier().split(":")[1]

    def get_pad_names(self) -> list[str]:
        # FIX: is_kicad_pad is not a child of is_kicad_footprint, but of
        # the sibling node of the parent of is_kicad_footprint
        return [
            p.get_trait(is_kicad_pad).get_pad_name()
            for p in self.get_children(
                direct_only=False, types=fabll.Node, required_trait=is_kicad_pad
            )
        ]

    @classmethod
    def MakeChild(cls, kicad_identifier: str) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.kicad_identifier_], kicad_identifier
            )
        )
        return out

    def setup(self, kicad_identifier: str) -> Self:
        self.kicad_identifier_.get().alias_to_single(
            g=self.instance.g(), value=kicad_identifier
        )
        return self


class is_generated_from_kicad_footprint_file(fabll.Node):
    """
    Marks a node as being generated from a KiCad footprint file.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()
    library_name_ = F.Parameters.StringParameter.MakeChild()
    kicad_footprint_file_path_ = F.Parameters.StringParameter.MakeChild()
    pad_names_ = F.Parameters.StringParameter.MakeChild()
    kicad_identifier_ = F.Parameters.StringParameter.MakeChild()

    @property
    def library_name(self) -> str:
        return self.library_name_.get().force_extract_literal().get_values()[0]

    @property
    def kicad_library_id(self) -> str:
        return self.kicad_identifier_.get().force_extract_literal().get_values()[0]

    @property
    def kicad_footprint_file_path(self) -> str:
        return (
            self.kicad_footprint_file_path_.get()
            .force_extract_literal()
            .get_values()[0]
        )

    @property
    def pad_names(self) -> list[str]:
        return self.pad_names_.get().force_extract_literal().get_values()

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
        kicad_footprint_file: "kicad.footprint.FootprintFile", library_name: str | None
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
    def MakeChild(
        cls, library_name: str | None, kicad_footprint_file_path: str
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        fp_file = kicad.loads(
            kicad.footprint.FootprintFile, Path(kicad_footprint_file_path)
        )
        kicad_identifier, library_name = cls._create_kicad_identifier(
            fp_file, library_name
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.kicad_identifier_], kicad_identifier
            )
        )
        pad_names = cls._extract_pad_names_from_kicad_footprint_file(fp_file)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.pad_names_], *pad_names
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.library_name_], library_name
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.kicad_footprint_file_path_], kicad_footprint_file_path
            )
        )
        return out

    def setup(
        self,
        kicad_footprint_file_path: str,
        library_name: str | None,
    ) -> Self:
        self.kicad_footprint_file_path_.get().alias_to_single(
            value=kicad_footprint_file_path
        )

        fp_file = kicad.loads(
            kicad.footprint.FootprintFile, Path(kicad_footprint_file_path)
        )
        pad_names = self._extract_pad_names_from_kicad_footprint_file(fp_file)
        self.pad_names_.get().alias_to_literal(*pad_names)
        kicad_identifier, library_name = self._create_kicad_identifier(
            fp_file, library_name
        )
        self.kicad_identifier_.get().alias_to_single(value=kicad_identifier)
        self.library_name_.get().alias_to_single(value=library_name)
        return self


class has_linked_kicad_footprint(fabll.Node):
    """
    A node that has a linked KiCad footprint.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    footprint_ = F.Collections.Pointer.MakeChild()
    transformer_ = F.Parameters.StringParameter.MakeChild()

    @property
    def footprint(self) -> fabll.Node:
        """Return the KiCad footprint associated with this node"""
        return self.footprint_.get().deref()

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
            F.Collections.Pointer.MakeEdge([out, cls.footprint_], [footprint])
        )
        out.add_dependant(
            F.Collections.Pointer.MakeEdge(
                [out, cls.transformer_], [str(id(transformer))]
            )
        )
        return out


class has_linked_kicad_net(fabll.Node):
    """
    A node that has a linked KiCad net.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    net_ptr_ = F.Collections.Pointer.MakeChild()
    transformer_ = F.Parameters.StringParameter.MakeChild()

    @property
    def net(self):
        """Return the KiCad net associated with this node"""
        return self.net_ptr_.get().deref()

    def get_transformer(self) -> "PCB_Transformer":
        transformer_id = int(
            self.transformer_.get().force_extract_literal().get_values()[0]
        )
        return ctypes.cast(transformer_id, ctypes.py_object).value

    @classmethod
    def MakeChild(
        cls, net: fabll._ChildField[fabll.Node], transformer: "PCB_Transformer"
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(net)
        out.add_dependant(
            F.Collections.Pointer.MakeEdge(
                [out, cls.transformer_], [str(id(transformer))]
            )
        )
        return out


class is_kicad_net(fabll.Node):
    """
    A node that is a KiCad net.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()


class has_associated_net(fabll.Node):
    """
    Link between pad-node and net. Added during build process.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    net_ptr_ = F.Collections.Pointer.MakeChild()

    @property
    def net(self) -> "F.Net":
        """Return the net associated with this node"""
        return self.net_ptr_.get().deref().cast(F.Net)

    @classmethod
    def MakeChild(cls, net: "fabll._ChildField[F.Net]") -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(net)
        return out


class GenericKiCadFootprint(fabll.Node):
    is_kicad_footprint_ = fabll.Traits.MakeEdge(is_kicad_footprint.MakeChild(""))
    kicad_pads_ = F.Collections.PointerSet.MakeChild()


class GenericKiCadPad(fabll.Node):
    is_kicad_pad_ = fabll.Traits.MakeEdge(is_kicad_pad.MakeChild(""))
    pad_name_ = F.Parameters.StringParameter.MakeChild()


def test_is_kicad_footprint():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class KCFootprint(fabll.Node):
        class KCPad(fabll.Node):
            _is_kicad_pad = fabll.Traits.MakeEdge(is_kicad_pad.MakeChild(pad_name="P1"))

        is_kicad_footprint = fabll.Traits.MakeEdge(
            is_kicad_footprint.MakeChild(
                kicad_identifier="Resistor:libR_0402_1005Metric2"
            )
        )
        kc_pad = KCPad.MakeChild()

    kicad_footprint = KCFootprint.bind_typegraph(tg=tg).create_instance(g=g)

    assert (
        kicad_footprint.is_kicad_footprint.get().get_kicad_footprint_identifier()
        == "Resistor:libR_0402_1005Metric2"
    )
    assert (
        kicad_footprint.is_kicad_footprint.get().get_kicad_footprint_name()
        == "libR_0402_1005Metric2"
    )
    kc_fp_trait = kicad_footprint.is_kicad_footprint.get()
    pad_names = kc_fp_trait.get_pad_names()

    assert len(pad_names) == 1
    assert pad_names[0] == "P1"


def test_has_linked_kicad_footprint():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class TestKiCadFootprint(fabll.Node):
        is_kicad_footprint_ = fabll.Traits.MakeEdge(
            is_kicad_footprint.MakeChild("ABC_lib:ABC_PART")
        )

    class TestFootprint(fabll.Node):
        is_footprint_ = fabll.Traits.MakeEdge(F.Footprints.is_footprint.MakeChild())
        has_linked_kicad_footprint_ = fabll.Traits.MakeEdge(
            has_linked_kicad_footprint.MakeChild(
                TestKiCadFootprint.MakeChild(), transformer=None
            )
        )
        pads_ = F.Collections.PointerSet.MakeChild()  # TODO

    fp = TestFootprint.bind_typegraph(tg=tg).create_instance(g=g)
    k_fp = fp.has_linked_kicad_footprint_.get().footprint
    assert k_fp.has_trait(is_kicad_footprint)
    assert (
        k_fp.get_trait(is_kicad_footprint).get_kicad_footprint_identifier()
        == "ABC_lib:ABC_PART"
    )


def test_is_generated_by_kicad_footprint():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    # class TestKiCadFootprint(fabll.Node):
    #     _is_kicad_footprint = fabll.Traits.MakeEdge(F.is_kicad_footprint.MakeChild())
    #     _is_generated_by_kicad_footprint = fabll.Traits.MakeEdge(
    #         is_generated_by_kicad_footprint.MakeChild(
    #             kicad_library_id="1234", kicad_footprint_file_path=""
    #         )
    #     )

    # class TestFootprint(fabll.Node):

    #     _is_footprint = fabll.Traits.MakeEdge(F.is_footprint.MakeChild())
    #     _has_linked_kicad_footprint = fabll.Traits.MakeEdge(
    #         F.has_linked_kicad_footprint.MakeChild(
    #             footprint=TestKiCadFootprint.MakeChild(), transformer=None
    #         )
    #     )

    # fp = TestFootprint.bind_typegraph(tg).create_instance(g=g)
    # kfp = fp.get_trait(F.has_linked_kicad_footprint)
    # gen_kfp_trait = kfp.get_trait(is_generated_by_kicad_footprint)
    # assert gen_kfp_trait.kicad_library_id == "1234"
    # assert gen_kfp_trait.kicad_footprint_file_path == ""
    # assert gen_kfp_trait.pad_names == []

    class NodeWithAssociatedFootprint(fabll.Node):
        """User defined node that can attach to a footprint"""

        _is_mmodule = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        _can_attach_to_footprint = fabll.Traits.MakeEdge(
            F.Footprints.can_attach_to_footprint.MakeChild()
        )

    user_node = NodeWithAssociatedFootprint.bind_typegraph(tg).create_instance(g=g)

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
        node=user_node, trait=is_generated_from_kicad_footprint_file
    ).setup(kicad_footprint_file_path=str(FPFILE), library_name="smol_part_lib")

    assert user_node.has_trait(is_generated_from_kicad_footprint_file)

    gen_kfp_trait = user_node.get_trait(is_generated_from_kicad_footprint_file)
    fp_names = is_generated_from_kicad_footprint_file._extract_pad_names_from_kicad_footprint_file(  # noqa: E501
        fp_file
    )

    assert gen_kfp_trait.kicad_library_id == "smol_part_lib:LED_0201_0603Metric"
    assert gen_kfp_trait.library_name == "smol_part_lib"
    assert gen_kfp_trait.kicad_footprint_file_path == str(FPFILE)
    assert gen_kfp_trait.pad_names == fp_names
