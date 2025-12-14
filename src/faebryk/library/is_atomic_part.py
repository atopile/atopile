# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F  # noqa: F401
from faebryk.libs.util import once


class is_atomic_part(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    manufacturer = F.Parameters.StringParameter.MakeChild()
    partnumber = F.Parameters.StringParameter.MakeChild()
    footprint = F.Parameters.StringParameter.MakeChild()
    symbol = F.Parameters.StringParameter.MakeChild()
    model = F.Parameters.StringParameter.MakeChild()

    is_lazy = fabll.Traits.MakeEdge(F.is_lazy.MakeChild())

    def get_manufacturer(self) -> str:
        return self.manufacturer.get().force_extract_literal().get_values()[0]

    def get_partnumber(self) -> str:
        return self.partnumber.get().force_extract_literal().get_values()[0]

    def get_footprint(self) -> str:
        return self.footprint.get().force_extract_literal().get_values()[0]

    def get_symbol(self) -> str:
        return self.symbol.get().force_extract_literal().get_values()[0]

    def get_model(self) -> str | None:
        literal = self.model.get().try_extract_constrained_literal()
        return None if literal is None else literal.get_values()[0]

    @property
    @once
    def path(self) -> Path:
        from atopile.compiler.front_end import from_dsl

        if (from_dsl_ := self.try_get_trait(from_dsl)) is None:
            raise ValueError(
                "No source context found for module with is_atomic_part trait"
            )

        if from_dsl_.src_file is None:
            raise ValueError(
                "No source file found for module with is_atomic_part trait"
            )

        return from_dsl_.src_file.parent

    # previous implementation of from_dsl from front_end
    # class from_dsl(Trait.decless()):
    # def __init__(
    #     self,
    #     src_ctx: ParserRuleContext,
    #     definition_ctx: ap.BlockdefContext | type[L.Node] | None = None,
    # ) -> None:
    #     super().__init__()
    #     self.src_ctx = src_ctx
    #     self.definition_ctx = definition_ctx
    #     self.references: list[Span] = []

    #     # just a failsafe
    #     if str(self.src_file.parent).startswith("file:"):
    #         raise ValueError(f"src_file: {self.src_file}")

    # def add_reference(self, ctx: ParserRuleContext) -> None:
    #     self.references.append(Span.from_ctx(ctx))

    # def add_composite_reference(self, *ctxs: ParserRuleContext) -> None:
    #     self.references.append(Span.from_ctxs(ctxs))

    # def set_definition(self, ctx: ap.BlockdefContext | type[L.Node]) -> None:
    #     self.definition_ctx = ctx

    # def query_references(self, file_path: str, line: int, col: int) -> Span | None:
    #     # TODO: faster
    #     for ref in self.references:
    #         if ref.contains(Position(file_path, line, col)):
    #             return ref
    #     return None

    @property
    def fp_path(self) -> tuple[Path, str]:
        return self.path / self.get_footprint(), str(self.path.name)

    def on_obj_set(self):
        parent = self.get_parent_force()[0]

        fp_path, fp_lib = self.fp_path
        fp = (
            F.KicadFootprint.bind_typegraph_from_instance(instance=self.instance)
            .create_instance(g=self.instance.g())
            .from_path(fp_path, lib_name=fp_lib)
        )
        # TODO: This trait is forwarded by a trait with attach function
        parent.get_trait(F.Footprints.can_attach_to_footprint).attach(fp)

        # TODO symbol

    @classmethod
    def MakeChild(
        cls,
        manufacturer: str,
        partnumber: str,
        footprint: str,
        symbol: str,
        model: str | None = None,
    ) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.manufacturer], manufacturer
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.partnumber], partnumber
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.footprint], footprint
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral([out, cls.symbol], symbol)
        )
        if model is not None:
            out.add_dependant(
                F.Literals.Strings.MakeChild_ConstrainToLiteral([out, cls.model], model)
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
        self.manufacturer.get().alias_to_single(value=manufacturer)
        self.partnumber.get().alias_to_single(value=partnumber)
        self.footprint.get().alias_to_single(value=footprint)
        self.symbol.get().alias_to_single(value=symbol)
        if model is not None:
            self.model.get().alias_to_single(value=model)
        return self
