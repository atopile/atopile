# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F  # noqa: F401
from faebryk.libs.util import once


class is_atomic_part(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    manufacturer_ = F.Parameters.StringParameter.MakeChild()
    partnumber_ = F.Parameters.StringParameter.MakeChild()
    footprint_ = F.Parameters.StringParameter.MakeChild()
    symbol_ = F.Parameters.StringParameter.MakeChild()
    model_ = F.Parameters.StringParameter.MakeChild()

    lazy: F.is_lazy

    @property
    def manufacturer(self) -> str:
        return str(self.manufacturer_.get().force_extract_literal())

    @property
    def partnumber(self) -> str:
        return str(self.partnumber_.get().force_extract_literal())

    @property
    def footprint(self) -> str:
        return str(self.footprint_.get().force_extract_literal())

    @property
    def symbol(self) -> str:
        return str(self.symbol_.get().force_extract_literal())

    @property
    def model(self) -> str | None:
        literal = self.model_.get().try_extract_constrained_literal()
        return None if literal is None else str(literal)

    @property
    @once
    def path(self) -> Path:
        from atopile.front_end import from_dsl

        if (from_dsl_ := self.try_get_trait(from_dsl)) is None:
            raise ValueError(
                "No source context found for module with is_atomic_part trait"
            )

        if from_dsl_.src_file is None:
            raise ValueError(
                "No source file found for module with is_atomic_part trait"
            )

        return from_dsl_.src_file.parent

    @property
    def fp_path(self) -> tuple[Path, str]:
        """
        returns path to footprint and library name
        """
        return self.path / self.footprint, str(self.path.name)

    def on_obj_set(self):
        parent = self.get_parent_force()[0]

        fp_path, fp_lib = self.fp_path
        fp = F.KicadFootprint.from_path(fp_path, lib_name=fp_lib)
        # TODO: This trait is forwarded by a trait with attach function
        parent.get_trait(F.can_attach_to_footprint).attach(fp)

        # TODO symbol

    @classmethod
    def MakeChild(
        cls,
        manufacturer: str,
        partnumber: str,
        footprint: str,
        symbol: str,
        model: str | None = None,
    ) -> fabll.ChildField:
        out = fabll.ChildField(cls)
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral(
                [out, cls.manufacturer_], manufacturer
            )
        )
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral(
                [out, cls.partnumber_], partnumber
            )
        )
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral(
                [out, cls.footprint_], footprint
            )
        )
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral([out, cls.symbol_], symbol)
        )
        if model is not None:
            out.add_dependant(
                F.Expressions.Is.MakeChild_ConstrainToLiteral([out, cls.model_], model)
            )
        return out

    def setup(
        self,
        manufacturer: str,
        partnumber: str,
        footprint: str,
        symbol: str,
        model: str | None = None,
    ) -> Self:
        self.manufacturer_.get().constrain_to_single(value=manufacturer)
        self.partnumber_.get().constrain_to_single(value=partnumber)
        self.footprint_.get().constrain_to_single(value=footprint)
        self.symbol_.get().constrain_to_single(value=symbol)
        if model is not None:
            self.model_.get().constrain_to_single(value=model)
        return self
