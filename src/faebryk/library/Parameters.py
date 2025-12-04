from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Self, cast

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import KeyErrorAmbiguous, not_none

if TYPE_CHECKING:
    import faebryk.library.Literals as Literals
    import faebryk.library.Units as Units
    from faebryk.library.NumberDomain import NumberDomain


class ContradictingLiterals(Exception):
    def __init__(self, literals: list["Literals.is_literal"], *args: object) -> None:
        super().__init__(*args)
        self.literals = literals

    def __str__(self) -> str:
        return f"ContradictingLiterals: {', '.join(lit.pretty_repr() for lit in self.literals)}"


class can_be_operand(fabll.Node):
    """
    Parameter, Expression, Literal
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def get_obj_type_node(self) -> graph.BoundNode:
        return not_none(fabll.Traits(self).get_obj_raw().get_type_node())

    def get_raw_obj(self) -> fabll.Node:
        return fabll.Traits(self).get_obj_raw()


class is_parameter_operatable(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    as_operand = fabll.Traits.ImpliedTrait(can_be_operand)

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
            node = self.as_operand.get()
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
            raise ParameterIsNotConstrainedToLiteral(parameter=self)
        return lit

    def alias_to_literal(
        self, g: graph.GraphView, value: "Literals.LiteralNodes"
    ) -> None:
        node = self.instance
        tg = not_none(fbrk.TypeGraph.of_instance(instance_node=node))
        from faebryk.library.Expressions import Is

        Is.bind_typegraph(tg=tg).create_instance(g=g).setup(
            self.as_operand.get(),
            value.is_literal.get().as_operand.get(),
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
        from faebryk.library.Expressions import is_expression

        if expr := self.try_get_sibling_trait(is_expression):
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
        if not not_none(is_lit).is_subset_of(not_none(ss_lit), g=self.g, tg=self.tg):
            raise ContradictingLiterals(lits)
        return is_lit

    def try_extract_literal(
        self, allow_subset: bool = False
    ) -> "Literals.is_literal | None":
        if allow_subset:
            return self.try_get_subset_or_alias_literal()
        return self.try_get_aliased_literal()

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
        # Use the can_be_operand trait's instance, since that's where operand edges
        # are attached
        operand_instance = e_ctx._self.as_operand.get().instance
        if types is fabll.Node:
            fbrk.EdgeOperand.visit_expression_edges(
                bound_node=operand_instance,
                ctx=e_ctx,
                f=visit,
            )
        else:
            fbrk.EdgeOperand.visit_expression_edges_of_type(
                bound_node=operand_instance,
                expression_type=types.bind_typegraph(self.tg)
                .get_or_create_type()
                .node(),
                ctx=e_ctx,
                f=visit,
            )

        out = e_ctx.operations
        if recursive:
            # Create a copy to iterate, since we'll be modifying out
            for op in list(out):
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
        from faebryk.library.Expressions import has_implicit_constraints, is_expression

        if self.try_get_sibling_trait(has_implicit_constraints):
            return True
        if expr := self.get_sibling_trait(is_expression):
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
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    as_parameter_operatable = fabll.Traits.ImpliedTrait(is_parameter_operatable)
    as_operand = fabll.Traits.ImpliedTrait(can_be_operand)

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

    def domain_set(self) -> "F.Literals.is_literal":
        # TODO
        pass

    def get_likely_constrained(self) -> bool:
        # TODO
        pass


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
    is_parameter = fabll.Traits.MakeEdge(is_parameter.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(is_parameter_operatable.MakeChild())
    can_be_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())

    def try_extract_constrained_literal(self) -> "Literals.Strings | None":
        from faebryk.library.Literals import Strings

        return self.is_parameter_operatable.get().try_get_constrained_literal(
            lit_type=Strings
        )

    def force_extract_literal(self) -> "Literals.Strings":
        from faebryk.library.Literals import Strings

        return self.is_parameter_operatable.get().force_extract_literal(
            lit_type=Strings
        )

    # TODO get rid of this and replace with alias_to_literal
    def alias_to_single(self, value: str, g: graph.GraphView | None = None) -> None:
        return self.alias_to_literal(value, g=g)

    def alias_to_literal(self, *values: str, g: graph.GraphView | None = None) -> None:
        g = g or self.instance.g()
        from faebryk.library.Literals import Strings

        self.is_parameter_operatable.get().alias_to_literal(
            g=g,
            value=Strings.bind_typegraph(tg=self.tg)
            .create_instance(g=g)
            .setup_from_values(*values),
        )


class BooleanParameter(fabll.Node):
    is_parameter = fabll.Traits.MakeEdge(is_parameter.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(is_parameter_operatable.MakeChild())
    can_be_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())

    def try_extract_constrained_literal(self) -> "Literals.Booleans | None":
        from faebryk.library.Literals import Booleans

        return self.is_parameter_operatable.get().try_get_constrained_literal(
            lit_type=Booleans
        )

    def force_extract_literal(self) -> "Literals.Booleans":
        from faebryk.library.Literals import Booleans

        return self.is_parameter_operatable.get().force_extract_literal(
            lit_type=Booleans
        )

    def extract_single(self) -> bool:
        return self.force_extract_literal().get_single()

    def alias_to_single(self, value: bool, g: graph.GraphView | None = None) -> None:
        g = g or self.instance.g()
        from faebryk.library.Literals import Booleans

        self.is_parameter_operatable.get().alias_to_literal(
            g=g,
            value=Booleans.bind_typegraph_from_instance(
                instance=self.instance
            ).create_instance(
                self.instance.g(),
                attributes=Booleans.Attributes(has_true=value, has_false=not value),
            ),
        )


class EnumParameter(fabll.Node):
    is_parameter = fabll.Traits.MakeEdge(is_parameter.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(is_parameter_operatable.MakeChild())
    can_be_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())
    enum_domain_pointer = F.Collections.Pointer.MakeChild()

    def get_enum_type(self) -> "fabll.NodeT":
        return fabll.Node.bind_instance(
            instance=self.enum_domain_pointer.get().deref().instance
        )

    def try_extract_constrained_literal[T: "F.Literals.AbstractEnums"](
        self,
    ) -> "F.Literals.AbstractEnums | None":
        return self.is_parameter_operatable.get().try_get_constrained_literal(
            lit_type=F.Literals.AbstractEnums
        )

    def force_extract_literal(self) -> "F.Literals.AbstractEnums":
        return self.is_parameter_operatable.get().force_extract_literal(
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

        self.is_parameter_operatable.get().alias_to_literal(g=g, value=lit)

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
    is_parameter = fabll.Traits.MakeEdge(is_parameter.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(is_parameter_operatable.MakeChild())
    can_be_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())
    number_domain = F.Collections.Pointer.MakeChild()

    # domain = fabll.ChildField(NumberDomain)

    def get_units(self) -> "Units.is_unit":
        from faebryk.library.Units import has_unit

        return self.get_trait(has_unit).get_is_unit()

    def get_domain(self) -> "NumberDomain":
        return F.NumberDomain.bind_instance(
            instance=self.number_domain.get().deref().instance
        )

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
        self.is_parameter_operatable.get().alias_to_literal(g=g, value=value)

    def setup(
        self,
        *,
        units: "Units.is_unit",
        # hard constraints
        within: "Literals.Numbers | None" = None,
        domain: "NumberDomain | None" = None,
        # soft constraints
        soft_set: "Literals.Numbers | None" = None,
        guess: "Literals.Numbers | None" = None,
        tolerance_guess: float | None = None,
        likely_constrained: bool = False,
    ) -> Self:
        from faebryk.library.NumberDomain import NumberDomain
        from faebryk.library.Units import has_unit

        fabll.Traits.create_and_add_instance_to(self, has_unit).setup(unit=units)
        if domain is None:  # Default domain is unbounded
            domain = (
                NumberDomain.bind_typegraph(tg=self.tg)
                .create_instance(g=self.g)
                .setup(
                    args=NumberDomain.Args(
                        negative=True, zero_allowed=True, integer=False
                    )
                )
            )

        self.number_domain.get().point(
            fabll.Node.bind_instance(instance=domain.instance)
        )
        return self

    @classmethod
    def MakeChild(
        cls,
        unit: type[fabll.NodeT] | None = None,
        integer: bool = False,
        negative: bool = False,
        zero_allowed: bool = True,
    ):
        from faebryk.library.NumberDomain import NumberDomain

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
        from faebryk.library.Units import has_unit

        if unit:
            out.add_dependant(fabll.Traits.MakeEdge(has_unit.MakeChild(unit), [out]))

        domain = NumberDomain.MakeChild(
            negative=negative, zero_allowed=zero_allowed, integer=integer
        )
        out.add_dependant(domain)

        out.add_dependant(
            fabll.MakeEdge(
                [out, cls.number_domain],
                [domain],
                edge=fbrk.EdgePointer.build(identifier="number_domain", order=None),
            )
        )

        # out.add_dependant(
        #     *NumberDomain.MakeEdges(
        #         ref=[out, cls.domain],
        #         negative=negative,
        #         zero_allowed=zero_allowed,
        #         integer=integer,
        #     )
        # )
        return out

    def try_extract_aliased_literal(self) -> "Literals.Numbers | None":
        from faebryk.library.Literals import Numbers

        return self.is_parameter_operatable.get().try_get_constrained_literal(
            lit_type=Numbers
        )

    def force_extract_literal(self) -> "Literals.Numbers":
        from faebryk.library.Literals import Numbers

        return self.is_parameter_operatable.get().force_extract_literal(
            lit_type=Numbers
        )


# Binding context ----------------------------------------------------------------------


class BoundParameterContext:
    """
    Convenience context for binding parameter types and creating instances.

    Usage:
        ctx = BoundParameterContext(tg=tg, g=g)
        my_param = ctx.NumericParameter.setup(units=F .Units.Ohm)
    """

    def __init__(self, tg: graph.TypeGraph, g: graph.GraphView):
        self.tg = tg
        self.g = g
        self._bound: dict = {}

    def _get_bound(self, cls: type[fabll.NodeT]):
        if cls not in self._bound:
            self._bound[cls] = cls.bind_typegraph(tg=self.tg)
        return self._bound[cls]

    @property
    def StringParameter(self) -> StringParameter:
        return self._get_bound(StringParameter).create_instance(g=self.g)

    @property
    def BooleanParameter(self) -> BooleanParameter:
        return self._get_bound(BooleanParameter).create_instance(g=self.g)

    @property
    def EnumParameter(self) -> EnumParameter:
        return self._get_bound(EnumParameter).create_instance(g=self.g)

    @property
    def NumericParameter(self) -> NumericParameter:
        return self._get_bound(NumericParameter).create_instance(g=self.g)


# Tests --------------------------------------------------------------------------------


def test_try_get():
    from faebryk.library.Expressions import IsSubset
    from faebryk.library.Literals import Strings

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    p1 = StringParameter.bind_typegraph(tg=tg).create_instance(g=g)
    p1.alias_to_literal("a", "b")
    p1_po = p1.is_parameter_operatable.get()

    assert not_none(p1.try_extract_constrained_literal()).get_values() == ["a", "b"]

    ss_lit = (
        Strings.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_values("a", "b", "c")
    )
    IsSubset.bind_typegraph(tg).create_instance(g=g).setup(
        subset=p1.can_be_operand.get(),
        superset=ss_lit.is_literal.get().as_operand.get(),
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


def test_enum_param():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    from enum import Enum

    import faebryk.library._F as TF

    class ExampleNode(fabll.Node):
        class MyEnum(Enum):
            A = "a"
            B = "b"
            C = "c"
            D = "d"

        enum_p_tg = EnumParameter.MakeChild(enum_t=MyEnum)
        constraint = TF.Literals.AbstractEnums.MakeChild_ConstrainToLiteral(
            [enum_p_tg], MyEnum.B, MyEnum.C
        )

        _has_usage_example = TF.has_usage_example.MakeChild(
            example="",
            language=TF.has_usage_example.Language.ato,
        ).put_on_type()

    example_node = ExampleNode.bind_typegraph(tg=tg).create_instance(g=g)

    # Enum Literal Type Node
    atype = TF.Literals.EnumsFactory(ExampleNode.MyEnum)
    cls_n = cast(type[fabll.NodeT], atype)
    _ = cls_n.bind_typegraph(tg=tg).get_or_create_type()

    # Enum Parameter from TG
    enum_param = example_node.enum_p_tg.get()

    abstract_enum_type_node = enum_param.get_enum_type()
    # assert abstract_enum_type_node.is_same(enum_type_node)

    assert [
        (m.name, m.value)
        for m in F.Literals.AbstractEnums.get_all_members_of_type(
            node=abstract_enum_type_node, tg=tg
        )
    ] == [(m.name, m.value) for m in ExampleNode.MyEnum]

    assert F.Literals.AbstractEnums.get_enum_as_dict_for_type(
        node=abstract_enum_type_node, tg=tg
    ) == {m.name: m.value for m in ExampleNode.MyEnum}

    enum_lit = enum_param.force_extract_literal()
    assert enum_lit.get_values() == ["b", "c"]

    # Enum Parameter from instance graph
    enum_p_ig = EnumParameter.bind_typegraph(tg=tg).create_instance(g=g)
    enum_p_ig.alias_to_literal(ExampleNode.MyEnum.B, g=g)
    assert enum_p_ig.force_extract_literal().get_values() == ["b"]


def test_string_param():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    import faebryk.library._F as F

    string_p = StringParameter.bind_typegraph(tg=tg).create_instance(g=g)
    string_p.alias_to_literal("IG constrained")
    assert string_p.force_extract_literal().get_value() == "IG constrained"

    class ExampleStringParameter(fabll.Node):
        string_p_tg = StringParameter.MakeChild()
        constraint = F.Literals.Strings.MakeChild_ConstrainToLiteral(
            [string_p_tg], "TG constrained"
        )

    esp = ExampleStringParameter.bind_typegraph(tg=tg).create_instance(g=g)
    assert esp.string_p_tg.get().force_extract_literal().get_value() == "TG constrained"


def test_boolean_param():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    import faebryk.library._F as F

    boolean_p = BooleanParameter.bind_typegraph(tg=tg).create_instance(g=g)
    boolean_p.alias_to_single(value=True, g=g)
    assert boolean_p.force_extract_literal().get_values()[0]

    class ExampleBooleanParameter(fabll.Node):
        boolean_p_tg = BooleanParameter.MakeChild()
        constraint = F.Literals.Booleans.MakeChild_ConstrainToLiteral(
            [boolean_p_tg], True
        )

    ebp = ExampleBooleanParameter.bind_typegraph(tg=tg).create_instance(g=g)
    assert ebp.boolean_p_tg.get().force_extract_literal().get_values()[0]


def test_get_operations():
    """Test the get_operations method on is_parameter_operatable."""
    from faebryk.library.Expressions import Add, Is

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    # Create parameters
    p1 = NumericParameter.bind_typegraph(tg=tg).create_instance(g=g)
    p2 = NumericParameter.bind_typegraph(tg=tg).create_instance(g=g)
    p3 = NumericParameter.bind_typegraph(tg=tg).create_instance(g=g)

    # Get is_parameter_operatable traits
    p1_po = p1.is_parameter_operatable.get()
    p2_po = p2.is_parameter_operatable.get()
    p3_po = p3.is_parameter_operatable.get()

    # Initially, no operations
    assert p1_po.get_operations() == set()
    assert p2_po.get_operations() == set()

    # Create an Add expression: p1 + p2
    add_expr = (
        Add.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup(p1.can_be_operand.get(), p2.can_be_operand.get())
    )

    # Now p1 and p2 should have the Add in their operations
    p1_ops = p1_po.get_operations()
    p2_ops = p2_po.get_operations()
    assert len(p1_ops) == 1
    assert len(p2_ops) == 1
    assert add_expr in p1_ops
    assert add_expr in p2_ops

    # p3 still has no operations
    assert p3_po.get_operations() == set()

    # Create an Is expression (predicate): Is(p1, p3)
    is_expr = (
        Is.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup(
            p1.can_be_operand.get(),
            p3.can_be_operand.get(),
            assert_=True,  # This makes it a predicate
        )
    )

    # p1 should now have both Add and Is in operations
    p1_ops_all = p1_po.get_operations()
    assert len(p1_ops_all) == 2
    assert add_expr in p1_ops_all
    assert is_expr in p1_ops_all

    # p3 should have Is
    p3_ops = p3_po.get_operations()
    assert len(p3_ops) == 1
    assert is_expr in p3_ops

    # Test filtering by type - only Add expressions
    p1_add_ops = p1_po.get_operations(types=Add)
    assert len(p1_add_ops) == 1
    assert add_expr in p1_add_ops
    assert is_expr not in p1_add_ops

    # Test filtering by type - only Is expressions
    p1_is_ops = p1_po.get_operations(types=Is)
    assert len(p1_is_ops) == 1
    assert is_expr in p1_is_ops
    assert add_expr not in p1_is_ops

    # Test predicates_only filter - should only return asserted expressions
    p1_predicates = p1_po.get_operations(predicates_only=True)
    assert is_expr in p1_predicates
    # Add is not a predicate (not asserted)
    assert add_expr not in p1_predicates

    # Test combined type + predicates_only
    p1_is_predicates = p1_po.get_operations(types=Is, predicates_only=True)
    assert is_expr in p1_is_predicates


def test_get_operations_recursive():
    """Test the recursive option of get_operations."""
    from faebryk.library.Expressions import Add, Multiply

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    # Create parameters
    p1 = NumericParameter.bind_typegraph(tg=tg).create_instance(g=g)
    p2 = NumericParameter.bind_typegraph(tg=tg).create_instance(g=g)
    p3 = NumericParameter.bind_typegraph(tg=tg).create_instance(g=g)

    p1_po = p1.is_parameter_operatable.get()
    # Create nested expressions: (p1 + p2) * p3
    add_expr = Add.c(
        p1.can_be_operand.get(),
        p2.can_be_operand.get(),
    )

    mul_expr = Multiply.c(
        add_expr,
        p3.can_be_operand.get(),
    )

    # Non-recursive: p1 only sees the Add directly
    p1_ops_non_recursive = p1_po.get_operations(recursive=False)
    assert fabll.Traits(add_expr).get_obj(Add) in p1_ops_non_recursive
    assert fabll.Traits(mul_expr).get_obj(Multiply) not in p1_ops_non_recursive

    # Recursive: p1 sees both Add and Multiply (through the Add)
    p1_ops_recursive = p1_po.get_operations(recursive=True)
    assert fabll.Traits(add_expr).get_obj(Add) in p1_ops_recursive
    assert fabll.Traits(mul_expr).get_obj(Multiply) in p1_ops_recursive


if __name__ == "__main__":
    import typer

    typer.run(test_enum_param)
