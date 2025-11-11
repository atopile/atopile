from enum import Enum
from typing import TYPE_CHECKING

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import not_none

if TYPE_CHECKING:
    from faebryk.library.NumberDomain import NumberDomain


class is_parameter_operatable(fabll.Node):
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()

    def try_extract_constrained_literal[T: "F.Literals.LiteralNodes"](
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

    def force_extract_literal[T: "F.Literals.LiteralNodes"](
        self, lit_type: type[T]
    ) -> T:
        lit = self.try_extract_constrained_literal(lit_type=lit_type)
        if lit is None:
            raise ParameterIsNotConstrainedToLiteral(parameter=self)
        return lit

    def constrain_to_literal(
        self, g: graph.GraphView, value: "F.Literals.LiteralNodes"
    ) -> None:
        node = self.instance
        tg = not_none(fabll.TypeGraph.of_instance(instance_node=node))
        from faebryk.library.Expressions import Is

        Is.bind_typegraph(tg=tg).create_instance(g=g).setup(
            operands=[self, value], constrain=True
        )


class is_parameter(fabll.Node):
    _is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()


class ParameterIsNotConstrainedToLiteral(Exception):
    def __init__(self, parameter: fabll.Node):
        self.parameter = parameter


# --------------------------------------------------------------------------------------


class StringParameter(fabll.Node):
    _is_parameter = fabll.ChildField(is_parameter)
    _is_parameter_operatable = fabll.ChildField(is_parameter_operatable)

    def try_extract_constrained_literal(self) -> "F.Literals.Strings | None":
        return self.get_trait(is_parameter_operatable).try_extract_constrained_literal(
            lit_type=F.Literals.Strings
        )

    def force_extract_literal(self) -> "F.Literals.Strings":
        return self.get_trait(is_parameter_operatable).force_extract_literal(
            lit_type=F.Literals.Strings
        )

    def constrain_to_single(self, value: str) -> None:
        self._is_parameter_operatable.get().constrain_to_literal(
            g=self.instance.g(),
            value=F.Literals.Strings.bind_typegraph_from_instance(
                instance=self.instance
            )
            .create_instance(self.instance.g())
            .setup(value),
        )


class BooleanParameter(fabll.Node):
    _is_parameter = fabll.ChildField(is_parameter)
    _is_parameter_operatable = fabll.ChildField(is_parameter_operatable)

    def try_extract_constrained_literal(self) -> "F.Literals.Booleans | None":
        return self.get_trait(is_parameter_operatable).try_extract_constrained_literal(
            lit_type=F.Literals.Booleans
        )

    def force_extract_literal(self) -> "F.Literals.Booleans":
        return self.get_trait(is_parameter_operatable).force_extract_literal(
            lit_type=F.Literals.Booleans
        )

    def extract_single(self) -> bool:
        return self.force_extract_literal().get_single()

    def constrain_to_single(self, value: bool) -> None:
        self._is_parameter_operatable.get().constrain_to_literal(
            g=self.instance.g(),
            value=F.Literals.Booleans.bind_typegraph_from_instance(
                instance=self.instance
            )
            .create_instance(self.instance.g())
            .setup(value),
        )


class EnumParameter(fabll.Node):
    _is_parameter = fabll.ChildField(is_parameter)
    _is_parameter_operatable = fabll.ChildField(is_parameter_operatable)

    @classmethod
    def MakeChild(cls, enum_t: type[Enum]):
        out = fabll.ChildField(cls)
        # TODO
        return out

    def try_extract_constrained_literal(self) -> "F.Literals.Enums | None":
        return self.get_trait(is_parameter_operatable).try_extract_constrained_literal(
            lit_type=F.Literals.Enums
        )

    def force_extract_literal(self) -> "F.Literals.Enums":
        return self.get_trait(is_parameter_operatable).force_extract_literal(
            lit_type=F.Literals.Enums
        )


class NumericParameter(fabll.Node):
    _is_parameter = fabll.ChildField(is_parameter)
    _is_parameter_operatable = fabll.ChildField(is_parameter_operatable)

    # domain = fabll.ChildField(NumberDomain)

    def constrain_to_literal(
        self, g: graph.GraphView, value: "F.Literals.Numbers"
    ) -> None:
        self.get_trait(is_parameter_operatable).constrain_to_literal(g=g, value=value)

    @classmethod
    def MakeChild(
        cls,
        unit: type[fabll.NodeT],
        integer: bool = False,
        negative: bool = False,
        zero_allowed: bool = True,
    ):
        out = fabll.ChildField(cls)
        unit_instance = fabll.ChildField(unit, identifier=None)
        out.add_dependant(unit_instance)
        out.add_dependant(
            fabll.EdgeField(
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

    def try_extract_constrained_literal(self) -> "F.Literals.Numbers | None":
        return self.get_trait(is_parameter_operatable).try_extract_constrained_literal(
            lit_type=F.Literals.Numbers
        )

    def force_extract_literal(self) -> "F.Literals.Numbers":
        return self.get_trait(is_parameter_operatable).force_extract_literal(
            lit_type=F.Literals.Numbers
        )
