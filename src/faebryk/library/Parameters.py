from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll

# import faebryk.enum_sets as enum_sets
import faebryk.library._F as F
from faebryk.libs.util import not_none

if TYPE_CHECKING:
    from faebryk.library import Literals, NumberDomain


class is_parameter_operatable(fabll.Node):
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()

    def try_extract_constrained_literal[T: "Literals.LiteralNodes"](
        self, lit_type: type[T]
    ) -> T | None:
        # 1. find all Is! expressions parameter is involved in
        # 2. for each of those check if they have a literal operand of the correct type

        class E_Ctx:
            lit: T | None = None
            node = fabll.Traits(self).get_obj(fabll.Node)
            Lit = lit_type.bind_typegraph(tg=self.tg)
            LitT = lit_type

        Is = F.Expressions.Is.bind_typegraph(tg=self.tg)

        def visit(e_ctx: E_Ctx, edge: graph.BoundEdge) -> None:
            class Ctx:
                lit: T | None = None

            # check if Is is constrained
            expr = fbrk.EdgeOperand.get_expression_node(edge=edge.edge())
            is_expr = F.Expressions.Is.bind_instance(instance=edge.g().bind(node=expr))
            if not is_expr.has_trait(F.Expressions.IsConstrained):
                return

            # for each of those check if they have a literal operand
            def visit(ctx: Ctx, edge: graph.BoundEdge) -> None:
                operand = fabll.Node.bind_instance(
                    edge.g().bind(node=edge.edge().target())
                )
                if e_ctx.Lit.isinstance(instance=operand):
                    ctx.lit = e_ctx.LitT.bind_instance(operand.instance)

            ctx = Ctx()
            fbrk.EdgeOperand.visit_operand_edges(
                bound_node=is_expr.instance, ctx=ctx, f=visit
            )
            e_ctx.lit = ctx.lit

        e_ctx = E_Ctx()
        fbrk.EdgeOperand.visit_expression_edges_of_type(
            bound_node=e_ctx.node.instance,
            expression_type=Is.get_or_create_type().node(),
            ctx=e_ctx,
            f=visit,
        )

        return e_ctx.lit

    def force_extract_literal[T: "Literals.LiteralNodes"](self, lit_type: type[T]) -> T:
        lit = self.try_extract_constrained_literal(lit_type=lit_type)
        if lit is None:
            raise ParameterIsNotConstrainedToLiteral(parameter=self)
        return lit

    def constrain_to_literal(
        self, g: graph.GraphView, value: "Literals.LiteralNodes"
    ) -> None:
        node = self.instance
        tg = not_none(fbrk.TypeGraph.of_instance(instance_node=node))
        from faebryk.library.Expressions import Is

        Is.bind_typegraph(tg=tg).create_instance(g=g).setup(
            operands=[self, value], constrain=True
        )

    def compact_repr(
        self, context: "ReprContext | None" = None, use_name: bool = False
    ) -> str:
        if p := fabll.Traits(self).try_get_trait_of_obj(is_parameter):
            return p.compact_repr(context=context, use_name=use_name)
        if e := fabll.Traits(self).try_get_trait_of_obj(is_parameter_operatable):
            return e.compact_repr(context=context, use_name=use_name)

        raise NotImplementedError()

    def get_depth(self) -> int:
        # TODO
        pass

    def try_get_literal(self) -> "Literals.LiteralNodes | None":
        # TODO
        pass

    def try_extract_literal(
        self, allow_subset: bool = False
    ) -> "Literals.LiteralNodes | None":
        # TODO
        pass

    def as_parameter(self) -> "is_parameter":
        return fabll.Traits(self).get_trait_of_obj(is_parameter)

    def as_expression(self) -> "F.Expressions.is_expression":
        return fabll.Traits(self).get_trait_of_obj(F.Expressions.is_expression)


class is_parameter(fabll.Node):
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()

    def compact_repr(
        self, context: "ReprContext | None" = None, use_name: bool = False
    ) -> str:
        # TODO
        raise NotImplementedError()

    def domain_set(self) -> "Literals.LiteralNodes":
        # TODO
        raise NotImplementedError()

    def get_likely_constrained(self) -> bool:
        # TODO
        pass

    def as_parameter_operatable(self) -> "is_parameter_operatable":
        return fabll.Traits(self).get_trait_of_obj(is_parameter_operatable)


class ParameterIsNotConstrainedToLiteral(Exception):
    def __init__(self, parameter: fabll.Node):
        self.parameter = parameter


@dataclass
class ReprContext:
    @dataclass
    class VariableMapping:
        mapping: dict[is_parameter, int] = field(default_factory=dict)
        next_id: int = 0

    variable_mapping: VariableMapping = field(default_factory=VariableMapping)

    def __hash__(self) -> int:
        return hash(id(self))


# --------------------------------------------------------------------------------------


class StringParameter(fabll.Node):
    _is_parameter = fabll.Traits.MakeChild_Trait(fabll._ChildField(is_parameter))
    _is_parameter_operatable = fabll.Traits.MakeChild_Trait(
        fabll._ChildField(is_parameter_operatable)
    )

    def try_extract_constrained_literal(self) -> "Literals.Strings | None":
        return self.get_trait(is_parameter_operatable).try_extract_constrained_literal(
            lit_type=F.Literals.Strings
        )

    def force_extract_literal(self) -> "Literals.Strings":
        return self.get_trait(is_parameter_operatable).force_extract_literal(
            lit_type=F.Literals.Strings
        )

    def constrain_to_single(self, value: str, g: graph.GraphView | None = None) -> None:
        g = g or self.instance.g()
        self._is_parameter_operatable.get().constrain_to_literal(
            g=g,
            value=F.Literals.Strings.bind_typegraph_from_instance(
                instance=self.instance
            )
            .create_instance(g)
            .setup(value),
        )


class BooleanParameter(fabll.Node):
    _is_parameter = fabll.Traits.MakeChild_Trait(fabll._ChildField(is_parameter))
    _is_parameter_operatable = fabll.Traits.MakeChild_Trait(
        fabll._ChildField(is_parameter_operatable)
    )

    def try_extract_constrained_literal(self) -> "Literals.Booleans | None":
        return self.get_trait(is_parameter_operatable).try_extract_constrained_literal(
            lit_type=F.Literals.Booleans
        )

    def force_extract_literal(self) -> "Literals.Booleans":
        return self.get_trait(is_parameter_operatable).force_extract_literal(
            lit_type=Literals.Booleans
        )

    def extract_single(self) -> bool:
        return self.force_extract_literal().get_single()

    def constrain_to_single(self, value: bool) -> None:
        self._is_parameter_operatable.get().constrain_to_literal(
            g=self.instance.g(),
            value=Literals.Booleans.bind_typegraph_from_instance(instance=self.instance)
            .create_instance(self.instance.g())
            .setup(value),
        )


class EnumParameter(fabll.Node):
    _is_parameter = fabll.Traits.MakeChild_Trait(fabll._ChildField(is_parameter))
    _is_parameter_operatable = fabll.Traits.MakeChild_Trait(
        fabll._ChildField(is_parameter_operatable)
    )

    @classmethod
    def MakeChild(cls, enum_t: type[Enum]):
        out = fabll._ChildField(cls)
        # TODO
        return out

    def try_extract_constrained_literal(self) -> "Literals.Enums | None":
        return self.get_trait(is_parameter_operatable).try_extract_constrained_literal(
            lit_type=Literals.Enums
        )

    def force_extract_literal(self) -> "Literals.Enums":
        return self.get_trait(is_parameter_operatable).force_extract_literal(
            lit_type=Literals.Enums
        )

    def setup(self, enum: type[Enum]) -> Self:
        # TODO
        return self

    def get_enum(self) -> type[Enum]:
        # TODO
        pass


class NumericParameter(fabll.Node):
    _is_parameter = fabll.Traits.MakeChild_Trait(fabll._ChildField(is_parameter))
    _is_parameter_operatable = fabll.Traits.MakeChild_Trait(
        fabll._ChildField(is_parameter_operatable)
    )

    # domain = fabll.ChildField(NumberDomain)

    def get_units(self) -> "Units.IsUnit":
        return self.get_trait(Units.HasUnit).get_unit()

    def get_domain(self) -> "NumberDomain":
        # TODO
        pass

    def get_within(self) -> "Literals.Numbers | None":
        # TODO
        pass

    def get_soft_set(self) -> "Literals.Numbers | None":
        # TODO
        pass

    def get_guess(self) -> "Literals.Numbers | None":
        # TODO
        pass

    def get_tolerance_guess(self) -> float | None:
        # TODO
        pass

    def constrain_to_literal(
        self, g: graph.GraphView, value: "Literals.Numbers"
    ) -> None:
        self.get_trait(is_parameter_operatable).constrain_to_literal(g=g, value=value)

    def setup(
        self,
        *,
        units: "Units.IsUnit",
        # hard constraints
        within: "Literals.Numbers | None" = None,
        domain: "NumberDomain | None" = None,
        # soft constraints
        soft_set: "Literals.Numbers | None" = None,
        guess: "Literals.Numbers | None" = None,
        tolerance_guess: float | None = None,
        likely_constrained: bool = False,
    ) -> Self:
        # TODO
        pass

    @classmethod
    def MakeChild(
        cls,
        unit: type[fabll.NodeT],
        integer: bool = False,
        negative: bool = False,
        zero_allowed: bool = True,
    ):
        out = fabll._ChildField(cls)
        unit_instance = fabll._ChildField(unit, identifier=None)
        out.add_dependant(unit_instance)
        out.add_dependant(
            fabll._EdgeField(
                [out],
                [unit_instance],
                edge=fbrk.EdgePointer.build(identifier="unit", order=None),
            )
        )
        # out.add_dependant(
        #     *NumberDomain.EdgeFields(
        #         ref=[out, cls.domain],
        #         negative=negative,
        #         zero_allowed=zero_allowed,
        #         integer=integer,
        #     )
        # )
        return out

    def try_extract_constrained_literal(self) -> "Literals.Numbers | None":
        return self.get_trait(is_parameter_operatable).try_extract_constrained_literal(
            lit_type=Literals.Numbers
        )

    def force_extract_literal(self) -> "Literals.Numbers":
        return self.get_trait(is_parameter_operatable).force_extract_literal(
            lit_type=Literals.Numbers
        )
