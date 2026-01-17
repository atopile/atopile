# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F


class is_atomic_part(fabll.Node):
    """Trait for atomic parts defined in .ato files with associated KiCad footprints."""

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    manufacturer = F.Parameters.StringParameter.MakeChild()
    partnumber = F.Parameters.StringParameter.MakeChild()
    footprint = F.Parameters.StringParameter.MakeChild()
    symbol = F.Parameters.StringParameter.MakeChild()
    model = F.Parameters.StringParameter.MakeChild()

    # Footprint node with is_footprint and kicad library footprint traits
    _footprint_node = fabll.Node.MakeChild()
    _is_footprint = fabll.Traits.MakeEdge(
        F.Footprints.is_footprint.MakeChild(), [_footprint_node]
    )
    # has_associated_kicad_library_footprint goes on the is_footprint trait instance
    _kicad_lib_fp = fabll.Traits.MakeEdge(
        fabll._ChildField(F.KiCadFootprints.has_associated_kicad_library_footprint),
        [_is_footprint],
    )

    # has_associated_footprint and can_attach_to_footprint as children
    _has_associated_footprint = F.Footprints.has_associated_footprint.MakeChild()
    _can_attach_to_footprint = F.Footprints.can_attach_to_footprint.MakeChild()

    # Point _has_associated_footprint.footprint_ to our _is_footprint
    _fp_pointer = F.Collections.Pointer.MakeEdge(
        [_has_associated_footprint, F.Footprints.has_associated_footprint.footprint_],
        [_is_footprint],
    )

    @classmethod
    def MakeChild(  # type: ignore[override]
        cls,
        manufacturer: str,
        partnumber: str,
        footprint: str,
        symbol: str,
        model: str | None = None,
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)

        # Constrain string parameters
        out.add_dependant(
            F.Literals.Strings.MakeChild_SetSuperset(
                [out, cls.manufacturer], manufacturer
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_SetSuperset([out, cls.partnumber], partnumber)
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_SetSuperset([out, cls.footprint], footprint)
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_SetSuperset([out, cls.symbol], symbol)
        )
        if model is not None:
            out.add_dependant(
                F.Literals.Strings.MakeChild_SetSuperset([out, cls.model], model)
            )

        owner_path: fabll.RefPath = fabll.SELF_OWNER_PLACEHOLDER
        out.add_dependant(
            fabll.MakeEdge(
                lhs=owner_path,
                rhs=[out, cls._has_associated_footprint],
                edge=fbrk.EdgeTrait.build(),
            )
        )
        out.add_dependant(
            fabll.MakeEdge(
                lhs=owner_path,
                rhs=[out, cls._can_attach_to_footprint],
                edge=fbrk.EdgeTrait.build(),
            )
        )

        return out

    def get_manufacturer(self) -> str:
        return self.manufacturer.get().extract_singleton()

    def get_partnumber(self) -> str:
        return self.partnumber.get().extract_singleton()

    def get_footprint(self) -> str:
        return self.footprint.get().extract_singleton()

    def get_symbol(self) -> str:
        return self.symbol.get().extract_singleton()

    def get_model(self) -> str | None:
        return self.model.get().try_extract_singleton()

    def get_source_dir(self) -> Path:
        """Get source directory from owner's is_ato_block trait."""
        from atopile.compiler.ast_visitor import is_ato_block

        owner = fabll.Traits.bind(self).get_obj(fabll.Node)
        ato_block = owner.get_trait(is_ato_block)
        return Path(ato_block.get_source_dir())

    def get_kicad_footprint_file_path(self) -> str:
        """Get full path to KiCad footprint file (source_dir / footprint)."""
        return str(self.get_source_dir() / self.get_footprint())

    def get_kicad_library_footprint(
        self,
    ) -> "F.KiCadFootprints.has_associated_kicad_library_footprint":
        """
        Get the has_associated_kicad_library_footprint trait, setting it up lazily.
        This only works at instance time when source_dir is available.
        """
        fp_trait = self._is_footprint.get()
        kicad_lib_fp = fp_trait.get_trait(
            F.KiCadFootprints.has_associated_kicad_library_footprint
        )

        # Check if already set up (has literal value)
        if kicad_lib_fp.kicad_footprint_file_path_.get().try_extract_singleton():
            return kicad_lib_fp

        # Lazily set up the trait with computed values
        fp_path = self.get_kicad_footprint_file_path()
        kicad_lib_fp.setup(
            kicad_footprint_file_path=fp_path,
            library_name=None,  # Will be derived from path
        )
        return kicad_lib_fp

    def setup(  # type: ignore[override]
        self,
        manufacturer: str,
        partnumber: str,
        footprint: str,
        symbol: str,
        model: str | None = None,
    ) -> Self:
        self.manufacturer.get().set_singleton(value=manufacturer)
        self.partnumber.get().set_singleton(value=partnumber)
        self.footprint.get().set_singleton(value=footprint)
        self.symbol.get().set_singleton(value=symbol)
        if model is not None:
            self.model.get().set_singleton(value=model)
        return self
