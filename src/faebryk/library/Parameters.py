from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Self, cast

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F

# import faebryk.enum_sets as enum_sets
from faebryk.libs.util import KeyErrorAmbiguous, not_none, once

if TYPE_CHECKING:
    import faebryk.library.Expressions as Expressions
    import faebryk.library.Literals as Literals
    import faebryk.library.Units as Units
    from faebryk.library.NumberDomain import NumberDomain


class is_parameter_operatable(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def try_get_constrained_literal[T: "fabll.NodeT" = "Literals.is_literal"](
        self,
        lit_type: type[T] | None = None,
        pred_type: type[fabll.NodeT] | None = None,
    ) -> T | None:
        # 1. find all Is! expressions parameter is involved in
        # 2. for each of those check if they have a literal operand of the correct type
        from faebryk.library.Expressions import Is as Is
        from faebryk.library.Expressions import IsSubset, is_predicate
        from faebryk.library.Literals import is_literal

        if pred_type is None:
            pred_type = Is

        # TODO: this is quite a hack
        if pred_type not in [Is, IsSubset]:
            raise ValueError(f"Invalid predicate type: {pred_type}")

        def _get_operand(expr: fabll.NodeT) -> fabll.NodeT:
            if pred_type is Is:
                return cast(fabll.NodeT, cast(Is, expr).operands.get())
            if pred_type is IsSubset:
                return cast(fabll.NodeT, cast(IsSubset, expr).superset.get())
            assert False

        Expr = pred_type.bind_typegraph(tg=self.tg)

        class E_Ctx:
            lit: is_literal | None = None
            node = self.as_operand()
            predT = pred_type

        def visit(e_ctx: E_Ctx, edge: graph.BoundEdge) -> None:
            class Ctx:
                lit: is_literal | None = None

            # check if Is is constrained
            expr_node = fbrk.EdgeOperand.get_expression_node(bound_edge=edge)
            expr = e_ctx.predT.bind_instance(instance=edge.g().bind(node=expr_node))
            if not expr.has_trait(is_predicate):
                return

            # for each of those check if they have a literal operand
            def visit(ctx: Ctx, edge: graph.BoundEdge) -> None:
                can_be_operand = fabll.Node.bind_instance(
                    edge.g().bind(node=edge.edge().target())
                )
                if lit := can_be_operand.try_get_sibling_trait(is_literal):
                    ctx.lit = lit

            ctx = Ctx()
            fbrk.EdgeOperand.visit_operand_edges(
                bound_node=cast(fabll.NodeT, _get_operand(expr)).instance,
                ctx=ctx,
                f=visit,
            )
            e_ctx.lit = ctx.lit

        e_ctx = E_Ctx()
        fbrk.EdgeOperand.visit_expression_edges_of_type(
            bound_node=e_ctx.node.instance,
            expression_type=Expr.get_or_create_type().node(),
            ctx=e_ctx,
            f=visit,
        )

        if isinstance(lit_type, fabll.Node):
            return e_ctx.lit

        if e_ctx.lit is not None and lit_type is not None:
            return fabll.Traits(e_ctx.lit).get_obj(lit_type)

        return cast("T|None", e_ctx.lit)

    def force_extract_literal[T: "fabll.NodeT" = "Literals.is_literal"](
        self, lit_type: type[T] | None = None
    ) -> T:
        lit = self.try_get_constrained_literal(lit_type=lit_type)
        if lit is None:
            print("NOT CONSTRAINED")
            raise ParameterIsNotConstrainedToLiteral(parameter=self)
        return lit

    def alias_to_literal(
        self, g: graph.GraphView, value: "Literals.LiteralNodes"
    ) -> None:
        node = self.instance
        tg = not_none(fbrk.TypeGraph.of_instance(instance_node=node))
        from faebryk.library.Expressions import Is

        Is.bind_typegraph(tg=tg).create_instance(g=g).setup(
            self.as_operand(),
            value.get_trait(can_be_operand),
            assert_=True,
        )

    def compact_repr(
        self, context: "ReprContext | None" = None, use_name: bool = False
    ) -> str:
        from faebryk.library.Expressions import is_expression

        if p := fabll.Traits(self).try_get_trait_of_obj(is_parameter):
            return p.compact_repr(context=context, use_name=use_name)
        if e := fabll.Traits(self).try_get_trait_of_obj(is_expression):
            return e.compact_repr(context=context, use_name=use_name)

        assert False

    def get_depth(self) -> int:
        if expr := self.is_expresssion():
            return expr.get_depth()
        return 0

    def try_get_aliased_literal(self) -> "Literals.is_literal | None":
        return self.try_get_constrained_literal()

    def try_get_subset_or_alias_literal(self) -> "Literals.is_literal | None":
        from faebryk.library.Expressions import Is, IsSubset

        is_lit = self.try_get_constrained_literal(pred_type=Is)
        ss_lit = self.try_get_constrained_literal(pred_type=IsSubset)
        lits = [lit for lit in [is_lit, ss_lit] if lit is not None]
        if not lits:
            return None
        if len(lits) == 1:
            return next(iter(lits))
        if not not_none(ss_lit).is_subset_of(not_none(is_lit)):
            raise KeyErrorAmbiguous(lits)
        return is_lit

    def try_extract_literal(
        self, allow_subset: bool = False
    ) -> "Literals.is_literal | None":
        if allow_subset:
            return self.try_get_subset_or_alias_literal()
        return self.try_get_aliased_literal()

    def as_parameter(self) -> "is_parameter":
        return fabll.Traits(self).get_trait_of_obj(is_parameter)

    def as_expression(self) -> "Expressions.is_expression":
        from faebryk.library.Expressions import is_expression

        return fabll.Traits(self).get_trait_of_obj(is_expression)

    def as_operand(self) -> "can_be_operand":
        return fabll.Traits(self).get_trait_of_obj(can_be_operand)

    def is_parameter(self) -> "is_parameter | None":
        return fabll.Traits(self).try_get_trait_of_obj(is_parameter)

    def is_expresssion(self) -> "Expressions.is_expression | None":
        from faebryk.library.Expressions import is_expression

        return fabll.Traits(self).try_get_trait_of_obj(is_expression)

    def get_operations[T: "fabll.NodeT"](
        self,
        types: type[T] = fabll.Node,
        predicates_only: bool = False,
        recursive: bool = False,
    ) -> set[T]:
        from faebryk.library.Expressions import is_predicate

        class E_Ctx:
            _self = self
            operations: set[T] = set()
            t = types
            predicates_only_: bool = predicates_only

        def visit(e_ctx: E_Ctx, edge: graph.BoundEdge) -> None:
            expr = fbrk.EdgeOperand.get_expression_node(bound_edge=edge)
            is_expr = fabll.Node.bind_instance(instance=edge.g().bind(node=expr))
            if e_ctx.predicates_only_ and not is_expr.has_trait(is_predicate):
                return

            e_ctx.operations.add(is_expr.cast(e_ctx.t))

        e_ctx = E_Ctx()
        if types is fabll.Node:
            fbrk.EdgeOperand.visit_expression_edges(
                bound_node=e_ctx._self.instance,
                ctx=e_ctx,
                f=visit,
            )
        else:
            fbrk.EdgeOperand.visit_expression_edges_of_type(
                bound_node=e_ctx._self.instance,
                expression_type=types.bind_typegraph(self.tg)
                .get_or_create_type()
                .node(),
                ctx=e_ctx,
                f=visit,
            )

        out = e_ctx.operations
        if recursive:
            for op in out:
                op_po = op.get_trait(is_parameter_operatable)
                out.update(
                    op_po.get_operations(
                        types=types,
                        predicates_only=predicates_only,
                        recursive=recursive,
                    )
                )

        return out

    def get_obj(self) -> "fabll.Node":
        return fabll.Traits(self).get_obj_raw()

    def has_implicit_predicates_recursive(self) -> bool:
        from faebryk.library.Expressions import has_implicit_constraints

        if self.try_get_sibling_trait(has_implicit_constraints):
            return True
        if expr := self.is_expresssion():
            return any(
                op.has_implicit_predicates_recursive()
                for op in expr.get_operand_operatables()
            )
        return False

    def _get_lit_suffix(self) -> str:
        out = ""
        try:
            lit = self.try_get_aliased_literal()
        except KeyErrorAmbiguous as e:
            return f"{{AMBIGUOUS_I: {e.duplicates}}}"
        if lit is not None:
            out = f"{{I|{lit.pretty_repr()}}}"
        elif (lit := self.try_get_subset_or_alias_literal()) is not None:
            out = f"{{S|{lit.pretty_repr()}}}"
        if lit and lit.equals_singleton(True):
            out = "✓"
        elif lit and lit.equals_singleton(False):
            out = "✗"
        return out


class is_parameter(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def compact_repr(
        self, context: "ReprContext | None" = None, use_name: bool = False
    ) -> str:
        """
        Unit only printed if not dimensionless.

        Letters:
        ```
        A-Z, a-z, α-ω
        A₁-Z₁, a₁-z₁, α₁-ω₁
        A₂-Z₂, a₂-z₂, α₂-ω₂
        ...
        ```
        """

        def param_id_to_human_str(param_id: int) -> str:
            assert isinstance(param_id, int)
            alphabets = [("A", 26), ("a", 26), ("α", 25)]
            alphabet = [
                chr(ord(start_char) + i)
                for start_char, char_cnt in alphabets
                for i in range(char_cnt)
            ]

            def int_to_subscript(i: int) -> str:
                if i == 0:
                    return ""
                _str = str(i)
                return "".join(chr(ord("₀") + ord(c) - ord("0")) for c in _str)

            return alphabet[param_id % len(alphabet)] + int_to_subscript(
                param_id // len(alphabet)
            )

        obj = fabll.Traits(self).get_obj_raw()
        if use_name and obj.get_parent() is not None:
            letter = obj.get_full_name()
        else:
            if context is None:
                context = ReprContext()
            if self not in context.variable_mapping.mapping:
                next_id = context.variable_mapping.next_id
                context.variable_mapping.mapping[self] = next_id
                context.variable_mapping.next_id += 1
            letter = param_id_to_human_str(context.variable_mapping.mapping[self])

        # TODO
        # unitstr = f" {self.units}" if self.units != dimensionless else ""
        unitstr = ""

        out = f"{letter}{unitstr}"
        out += self.get_sibling_trait(is_parameter_operatable)._get_lit_suffix()

        return out

    def domain_set(self) -> "Literals.is_literal":
        # TODO
        pass

    def get_likely_constrained(self) -> bool:
        # TODO
        pass

    def as_parameter_operatable(self) -> "is_parameter_operatable":
        return fabll.Traits(self).get_trait_of_obj(is_parameter_operatable)

    def as_operand(self) -> "can_be_operand":
        return fabll.Traits(self).get_trait_of_obj(can_be_operand)


class can_be_operand(fabll.Node):
    """
    Parameter, Expression, Literal
    """

    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def as_parameter_operatable(self) -> "is_parameter_operatable":
        return fabll.Traits(self).get_trait_of_obj(is_parameter_operatable)

    def is_parameter_operatable(self) -> "is_parameter_operatable | None":
        return fabll.Traits(self).try_get_trait_of_obj(is_parameter_operatable)

    def get_obj_type_node(self) -> graph.BoundNode:
        return not_none(fabll.Traits(self).get_obj_raw().get_type_node())


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
    _is_parameter = fabll.Traits.MakeEdge(is_parameter.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        is_parameter_operatable.MakeChild()
    )
    _can_be_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())

    def try_extract_constrained_literal(self) -> "Literals.Strings | None":
        from faebryk.library.Literals import Strings

        return self.get_trait(is_parameter_operatable).try_get_constrained_literal(
            lit_type=Strings
        )

    def force_extract_literal(self) -> "Literals.Strings":
        from faebryk.library.Literals import Strings

        return self.get_trait(is_parameter_operatable).force_extract_literal(
            lit_type=Strings
        )

    # TODO get rid of this and replace with alias_to_literal
    def alias_to_single(self, value: str, g: graph.GraphView | None = None) -> None:
        return self.alias_to_literal(value, g=g)

    def alias_to_literal(self, *values: str, g: graph.GraphView | None = None) -> None:
        g = g or self.instance.g()
        from faebryk.library.Literals import Strings

        self._is_parameter_operatable.get().alias_to_literal(
            g=g,
            value=Strings.bind_typegraph(tg=self.tg)
            .create_instance(g=g)
            .setup_from_values(*values),
        )


class BooleanParameter(fabll.Node):
    _is_parameter = fabll.Traits.MakeEdge(is_parameter.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        is_parameter_operatable.MakeChild()
    )
    _can_be_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())

    def try_extract_constrained_literal(self) -> "Literals.Booleans | None":
        from faebryk.library.Literals import Booleans

        return self.get_trait(is_parameter_operatable).try_get_constrained_literal(
            lit_type=Booleans
        )

    def force_extract_literal(self) -> "Literals.Booleans":
        from faebryk.library.Literals import Booleans

        return self.get_trait(is_parameter_operatable).force_extract_literal(
            lit_type=Booleans
        )

    def extract_single(self) -> bool:
        return self.force_extract_literal().get_single()

    def alias_to_single(self, value: bool, g: graph.GraphView | None = None) -> None:
        g = g or self.instance.g()
        from faebryk.library.Literals import Booleans

        self._is_parameter_operatable.get().alias_to_literal(
            g=g,
            value=Booleans.bind_typegraph_from_instance(
                instance=self.instance
            ).create_instance(
                self.instance.g(), attributes=Booleans.Attributes(value=value)
            ),
        )


class EnumParameter(fabll.Node):
    _is_parameter = fabll.Traits.MakeEdge(is_parameter.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        is_parameter_operatable.MakeChild()
    )
    _can_be_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())
    enum_domain_pointer = F.Collections.Pointer.MakeChild()

    def get_enum_type(self) -> "F.Literals.AbstractEnums":
        return F.Literals.AbstractEnums.bind_instance(
            instance=self.enum_domain_pointer.get().deref().instance
        )

    def try_extract_constrained_literal[T: "F.Literals.AbstractEnums"](
        self,
    ) -> "F.Literals.AbstractEnums | None":
        return self.get_trait(is_parameter_operatable).try_get_constrained_literal(
            lit_type=F.Literals.AbstractEnums
        )

    def force_extract_literal(self) -> "F.Literals.AbstractEnums":
        return self.get_trait(is_parameter_operatable).force_extract_literal(
            lit_type=F.Literals.AbstractEnums
        )

    def setup(self, enum: type[Enum]) -> Self:
        # TODO
        return self

    def alias_to_literal(
        self, *enum_members: Enum, g: graph.GraphView | None = None
    ) -> None:
        g = g or self.instance.g()
        from faebryk.library.Literals import AbstractEnums, EnumsFactory

        enum_type = EnumsFactory(type(enum_members[0]))
        enum_type_node = enum_type.bind_typegraph(tg=self.tg).get_or_create_type()
        self.enum_domain_pointer.get().point(
            fabll.Node.bind_instance(instance=enum_type_node)
        )

        lit = (
            AbstractEnums.bind_typegraph(tg=self.tg)
            .create_instance(g=g)
            .setup(*enum_members)
        )

        self._is_parameter_operatable.get().alias_to_literal(g=g, value=lit)

    @classmethod
    def MakeChild(cls, enum_t: type[Enum]) -> fabll._ChildField["Self"]:
        atype = F.Literals.EnumsFactory(enum_t)
        cls_n = cast(type[fabll.NodeT], atype)

        out = fabll._ChildField(cls)
        out.add_dependant(atype.MakeChild(*[member for member in enum_t]))
        out.add_dependant(
            fabll.MakeEdge(
                [out, cls.enum_domain_pointer],
                [cls_n],
                edge=fbrk.EdgePointer.build(
                    identifier="enum_domain_pointer", order=None
                ),
            )
        )

        return out

    @staticmethod
    def check_single_single_enum(params: list["EnumParameter"]) -> type[Enum]:
        enums = {p.get_enum() for p in params}
        if len(enums) != 1:
            raise ValueError("Multiple enum types found")
        return next(iter(enums))


class NumericParameter(fabll.Node):
    _is_parameter = fabll.Traits.MakeEdge(is_parameter.MakeChild())
    _is_parameter_operatable = fabll.Traits.MakeEdge(
        is_parameter_operatable.MakeChild()
    )
    _can_be_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())

    # domain = fabll.ChildField(NumberDomain)

    def get_units(self) -> "Units.IsUnit":
        from faebryk.library.Units import HasUnit

        return self.get_trait(HasUnit).get_unit()

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

    def alias_to_literal(self, g: graph.GraphView, value: "Literals.Numbers") -> None:
        self.get_trait(is_parameter_operatable).alias_to_literal(g=g, value=value)

    def setup(
        self,
        *,
        units: "Units.IsUnit | None" = None,
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
        return self

    @classmethod
    def MakeChild(
        cls,
        unit: type[fabll.NodeT],
        integer: bool = False,
        negative: bool = False,
        zero_allowed: bool = True,
    ):
        out = fabll._ChildField(cls)
        # unit_instance = fabll._ChildField(unit, identifier=None)
        # out.add_dependant(unit_instance)
        # out.add_dependant(
        #     fabll.MakeEdge(
        #         [out],
        #         [unit_instance],
        #         edge=fbrk.EdgePointer.build(identifier="unit", order=None),
        #     )
        # )
        from faebryk.library.Units import HasUnit

        out.add_dependant(fabll.Traits.MakeEdge(HasUnit.MakeChild(unit), [out]))
        # out.add_dependant(
        #     *NumberDomain.MakeEdges(
        #         ref=[out, cls.domain],
        #         negative=negative,
        #         zero_allowed=zero_allowed,
        #         integer=integer,
        #     )
        # )
        return out

    @classmethod
    def MakeChild_UnresolvedUnits(
        cls, integer: bool = False, negative: bool = False, zero_allowed: bool = True
    ) -> fabll._ChildField[Self]:
        """
        Used for bootstrapping units — consider using Dimensionless instead
        """
        out = fabll._ChildField(cls)
        # TODO
        return out

    def try_extract_aliased_literal(self) -> "Literals.Numbers | None":
        from faebryk.library.Literals import Numbers

        return self.get_trait(is_parameter_operatable).try_get_constrained_literal(
            lit_type=Numbers
        )

    def force_extract_literal(self) -> "Literals.Numbers":
        from faebryk.library.Literals import Numbers

        return self.get_trait(is_parameter_operatable).force_extract_literal(
            lit_type=Numbers
        )


# Binding context ----------------------------------------------------------------------


class BoundParameterContext:
    def __init__(self, tg: graph.TypeGraph, g: graph.GraphView):
        self.tg = tg
        self.g = g

    @property
    @once
    def StringParameter(self):
        return StringParameter.bind_typegraph(tg=self.tg)

    @property
    @once
    def BooleanParameter(self):
        return BooleanParameter.bind_typegraph(tg=self.tg)

    @property
    @once
    def EnumParameter(self):
        return EnumParameter.bind_typegraph(tg=self.tg)

    @property
    @once
    def NumericParameter(self):
        return NumericParameter.bind_typegraph(tg=self.tg)

    def create_string_parameter(self, value: str) -> "StringParameter":
        return self.StringParameter.create_instance(g=self.g).alias_to_single(
            value=value, g=self.g
        )

    def create_boolean_parameter(self, value: bool) -> "BooleanParameter":
        return self.BooleanParameter.create_instance(g=self.g).alias_to_single(
            value=value, g=self.g
        )

    def create_enum_parameter(self, enum: type[Enum]) -> "EnumParameter":
        return self.EnumParameter.create_instance(g=self.g).setup(enum=enum)

    def create_numeric_parameter(
        self,
        units: "Units.IsUnit | None" = None,
        within: "Literals.Numbers | None" = None,
        domain: "NumberDomain | None" = None,
        soft_set: "Literals.Numbers | None" = None,
        guess: "Literals.Numbers | None" = None,
        tolerance_guess: float | None = None,
        likely_constrained: bool = False,
    ) -> "NumericParameter":
        return self.NumericParameter.create_instance(g=self.g).setup(
            units=units,
            within=within,
            domain=domain,
            soft_set=soft_set,
            guess=guess,
            tolerance_guess=tolerance_guess,
            likely_constrained=likely_constrained,
        )


# Tests --------------------------------------------------------------------------------


def test_try_get():
    from faebryk.library.Expressions import IsSubset
    from faebryk.library.Literals import Strings

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    p1 = StringParameter.bind_typegraph(tg=tg).create_instance(g=g)
    p1.alias_to_literal("a", "b")
    p1_po = p1.get_trait(is_parameter_operatable)

    assert not_none(p1.try_extract_constrained_literal()).get_values() == ["a", "b"]

    ss_lit = (
        Strings.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_values("a", "b", "c")
    )
    IsSubset.bind_typegraph(tg).create_instance(g=g).setup(
        subset=p1.get_trait(can_be_operand),
        superset=ss_lit.get_trait(can_be_operand),
        assert_=True,
    )

    ss_lit_get = p1_po.try_get_constrained_literal(pred_type=IsSubset)
    assert ss_lit_get is not None
    assert fabll.Traits(ss_lit_get).get_obj(Strings).get_values() == [
        "a",
        "b",
        "c",
    ]

    ss_is_lit = p1_po.try_get_subset_or_alias_literal()
    assert ss_is_lit is not None
    assert fabll.Traits(ss_is_lit).get_obj(Strings).get_values() == [
        "a",
        "b",
    ]
