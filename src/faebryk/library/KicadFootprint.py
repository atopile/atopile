# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Self

import faebryk.core.node as fabll
import faebryk.library._F as F

if TYPE_CHECKING:
    from faebryk.libs.kicad.fileformats import kicad


class KicadFootprint(fabll.Node):
    class has_file(fabll.Node):
        """
        Direct reference to a KiCAD footprint file
        """

        _is_trait = fabll.Traits.MakeEdge(
            fabll.ImplementsTrait.MakeChild().put_on_type()
        )

        file_ = F.Parameters.StringParameter.MakeChild()

        @property
        def file(self) -> Path:
            return Path(str(self.file_.get().force_extract_literal()))

        def setup(self, file: PathLike) -> Self:
            self.file_.get().alias_to_single(value=str(file))
            return self

    class has_kicad_identifier(fabll.Node):
        _is_trait = fabll.Traits.MakeEdge(
            fabll.ImplementsTrait.MakeChild().put_on_type()
        )

        kicad_identifier_ = F.Parameters.StringParameter.MakeChild()

        @property
        def kicad_identifier(self) -> str:
            return str(self.kicad_identifier_.get().force_extract_literal())

        def setup(self, kicad_identifier: str) -> Self:
            self.kicad_identifier_.get().alias_to_single(value=kicad_identifier)
            return self

        def on_obj_set(self):
            # Implicit trait of has_kicad_footprint is added w/ this trait
            # If this changes, create_footprint_library will need to be updated
            fp = self.get_parent_force()[0].get_trait(KicadFootprint)
            if not fp.has_trait(F.has_kicad_footprint):
                fabll.Traits.create_and_add_instance_to(
                    node=fp, trait=F.has_kicad_footprint
                ).setup(
                    kicad_identifier=self.kicad_identifier,
                    pinmap={
                        fp.pins[i]: pin_name for i, pin_name in fp.pin_names_sorted
                    },
                )

    pin_names_ = F.Collections.PointerSet.MakeChild()
    pins_ = F.Collections.PointerSet.MakeChild()

    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    @property
    def pin_names(self) -> list[str]:
        pin_name_parameters = self.pin_names_.get().as_list()
        return [
            str(
                F.Parameters.StringParameter.bind_instance(
                    instance=pin_name_parameter.instance
                ).force_extract_literal()
            )
            for pin_name_parameter in pin_name_parameters
        ]

    @property
    def pin_names_sorted(self) -> list[tuple[int, str]]:
        return list(enumerate(sorted(set(self.pin_names))))

    @property
    def pins(self) -> list[F.Pad]:
        pin_pads = self.pins_.get().as_list()
        return [F.Pad.bind_instance(pin_pad.instance) for pin_pad in pin_pads]

    @classmethod
    def MakeChild(cls, pin_names: list[str]) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        for pin_name in pin_names:
            pin_parameter = F.Parameters.StringParameter.MakeChild()
            out.add_dependant(pin_parameter)
            out.add_dependant(
                F.Expressions.Is.MakeChild_ConstrainToLiteral([pin_parameter], pin_name)
            )
            out.add_dependant(
                F.Collections.PointerSet.MakeEdge([out, cls.pin_names_], [pin_name])
            )
            pin_pad = F.Pad.MakeChild()
            out.add_dependant(pin_pad)
            out.add_dependant(
                F.Collections.PointerSet.MakeEdge([out, cls.pins_], [pin_pad])
            )
        return out

    def setup(self, pin_names: list[str]) -> Self:
        for pin_name in pin_names:
            # Pin name parameters
            pin_parameter = F.Parameters.StringParameter.bind_typegraph_from_instance(
                instance=self.instance
            ).create_instance(g=self.instance.g())
            pin_parameter.alias_to_single(value=pin_name)
            self.pin_names_.get().append(pin_parameter)

            # Pads
            pad = F.Pad.bind_typegraph_from_instance(
                instance=self.instance
            ).create_instance(g=self.instance.g())
            self.pins_.get().append(pad)
        return self

    def setup_from_path(
        self, fp_path: PathLike, lib_name: str | None = None
    ) -> "KicadFootprint":
        """
        Create based on a footprint file

        Will take the pin names from that file.
        """
        from faebryk.libs.kicad.fileformats import kicad

        self = self.from_file(
            kicad.loads(kicad.footprint.FootprintFile, Path(fp_path)), lib_name=lib_name
        )
        fabll.Traits.create_and_add_instance_to(node=self, trait=self.has_file).setup(
            file=fp_path
        )
        return self

    def from_file(
        self, fp_file: "kicad.footprint.FootprintFile", lib_name: str | None = None
    ) -> "KicadFootprint":
        """
        Create based on a footprint file

        Will take the pin names from that file.
        """
        from faebryk.libs.kicad.fileformats import kicad

        if ":" in fp_file.footprint.name:
            fp_lib_name = fp_file.footprint.name.split(":")[0]
            if lib_name is not None and lib_name != fp_lib_name:
                raise ValueError(
                    f"lib_name must be empty or same as fp lib name, if fp has libname:"
                    f" fp_lib_name: {fp_lib_name}, lib_name: {lib_name}"
                )
            lib_name = fp_lib_name
        else:
            if lib_name is None:
                raise ValueError(
                    "lib_name must be specified if fp has no lib prefix: "
                    f"{fp_file.footprint.name}"
                )
        assert lib_name is not None

        pad_names = [pad.name for pad in fp_file.footprint.pads]
        self = self.setup(pad_names)
        fabll.Traits.create_and_add_instance_to(
            node=self, trait=self.has_kicad_identifier
        ).setup(
            kicad_identifier=f"{lib_name}:{kicad.fp_get_base_name(fp_file.footprint)}"
        )
        return self

    def from_path(
        self, fp_path: PathLike, lib_name: str | None = None
    ) -> "KicadFootprint":
        """
        Create based on a footprint file

        Will take the pin names from that file.
        """
        from faebryk.libs.kicad.fileformats import kicad

        self = self.from_file(
            kicad.loads(kicad.footprint.FootprintFile, Path(fp_path)), lib_name=lib_name
        )
        fabll.Traits.create_and_add_instance_to(node=self, trait=self.has_file).setup(
            file=fp_path
        )
        return self
