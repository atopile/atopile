import math
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Self, cast

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import KeyErrorAmbiguous, not_none, times

if TYPE_CHECKING:
    import faebryk.library.Literals as Literals
    import faebryk.library.Units as Units
    from faebryk.library.NumberDomain import NumberDomain


# Cached alphabet/subscript data for compact_repr to avoid per-call allocations.
_REPR_ALPHABET: tuple[str, ...] = tuple(
    [chr(ord("A") + i) for i in range(26)]
    + [chr(ord("a") + i) for i in range(26)]
    + [chr(ord("α") + i) for i in range(25)]
)
_SUBSCRIPT_TRANSLATION = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def _param_id_to_human_str(param_id: int) -> str:
    assert isinstance(param_id, int)
    letter = _REPR_ALPHABET[param_id % len(_REPR_ALPHABET)]
    suffix = param_id // len(_REPR_ALPHABET)
    if suffix == 0:
        return letter
    return letter + str(suffix).translate(_SUBSCRIPT_TRANSLATION)


class ContradictingLiterals(Exception):
    def __init__(self, literals: list["Literals.is_literal"], *args: object) -> None:
        super().__init__(*args)
        self.literals = literals

    def __str__(self) -> str:
        return (
            f"ContradictingLiterals:"
            f" {', '.join(lit.pretty_str() for lit in self.literals)}"
        )


class can_be_operand(fabll.Node):
    """
    Parameter, Expression, Literal
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    as_parameter_operatable: fabll.Traits.OptionalImpliedTrait[
        "is_parameter_operatable"
    ] = fabll.Traits.OptionalImpliedTrait(lambda: is_parameter_operatable)
    as_literal: fabll.Traits.OptionalImpliedTrait["F.Literals.is_literal"] = (
        fabll.Traits.OptionalImpliedTrait(lambda: F.Literals.is_literal)
    )

    def get_obj_type_node(self) -> graph.BoundNode:
        return not_none(fabll.Traits(self).get_obj_raw().get_type_node())

    def get_raw_obj(self) -> fabll.Node:
        return fabll.Traits(self).get_obj_raw()

    def pretty(self, use_name: bool = True) -> str:
        """Return context-aware string (pretty_str for literals, compact_repr else)."""
        if lit := self.as_literal.try_get():
            return lit.pretty_str()
        if po := self.as_parameter_operatable.try_get():
            return po.compact_repr(use_name=use_name)
        return str(self)

    def get_operations[T: "fabll.NodeT"](
        self,
        types: type[T] = fabll.Node,
        predicates_only: bool = False,
        recursive: bool = False,
    ) -> set[T]:
        # Import inside function to avoid gen_F.py cycle detection
        # (gen_F.py only looks for F.* patterns)
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
        operand_instance = e_ctx._self.instance
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

    def get_root_operands(self) -> set["can_be_operand"]:
        # Import inside function to avoid gen_F.py cycle detection
        from faebryk.library.Expressions import is_expression

        if expr := self.try_get_sibling_trait(is_expression):
            expr_leaves = expr.get_operand_leaves() | {self}
        else:
            expr_leaves = {self}

        all_expressions = {
            expr.get_trait(can_be_operand)
            for leaf in expr_leaves
            for expr in leaf.get_operations(recursive=True)
        }

        root_expressions = {
            root_expr for root_expr in all_expressions if not root_expr.get_operations()
        }

        if not root_expressions:
            return {self}

        return root_expressions


class is_parameter_operatable(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    as_operand = fabll.Traits.ImpliedTrait(can_be_operand)

    as_parameter: fabll.Traits.OptionalImpliedTrait["is_parameter"] = (
        fabll.Traits.OptionalImpliedTrait(lambda: is_parameter)
    )

    @staticmethod
    def _get_is_expression():
        """Deferred import to avoid circular dependency with Expressions module."""
        from faebryk.library.Expressions import is_expression

        return is_expression

    # TODO: is there a cleaner way to avoid adding Expressions dependency here?
    as_expression: fabll.Traits.OptionalImpliedTrait["F.Expressions.is_expression"] = (
        fabll.Traits.OptionalImpliedTrait(_get_is_expression)
    )

    def try_get_constrained_literal[T: "fabll.NodeT" = "Literals.is_literal"](
        self,
        lit_type: type[T] | None = None,
        pred_type: type[fabll.NodeT] | None = None,
    ) -> T | None:
        # 1. find all Is! expressions parameter is involved in
        # 2. for each of those check if they have a literal operand of the correct type
        from faebryk.library.Expressions import Is, IsSubset, is_commutative
        from faebryk.library.Literals import is_literal

        if pred_type is None:
            pred_type = Is

        # TODO: this is quite a hack
        if pred_type is not Is and pred_type is not IsSubset:
            raise ValueError(f"Invalid predicate type: {pred_type}")

        exprs = self.get_operations(types=pred_type, predicates_only=True)
        lits = []
        for expr in exprs:
            if expr.has_trait(is_commutative):
                if lit_vs := expr.is_expression.get().get_operand_literals().values():
                    lits.extend(lit_vs)
            else:
                ops = expr.is_expression.get().get_operands()
                for op in ops[1:]:
                    if lit := op.as_literal.try_get():
                        lits.append(lit)

        if not lits:
            return None
        lit_merged = F.Literals.is_literal.op_intersect_intervals(*lits)

        if lit_type is None or lit_type is is_literal:
            return cast(T, lit_merged)
        return fabll.Traits(lit_merged).get_obj(lit_type)

        return None

    def force_extract_literal[T: "fabll.NodeT" = "Literals.is_literal"](
        self,
        lit_type: type[T] | None = None,
        pred_type: type[fabll.NodeT] | None = None,
    ) -> T:
        lit = self.try_get_constrained_literal(lit_type=lit_type, pred_type=pred_type)
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
        self,
        context: "ReprContext | None" = None,
        use_name: bool = False,
        no_lit_suffix: bool = False,
    ) -> str:
        """Return compact math representation (delegates to parameter or expression)."""
        if p := self.as_parameter.try_get():
            return p.compact_repr(
                context=context, use_name=use_name, no_lit_suffix=no_lit_suffix
            )
        if e := self.as_expression.try_get():
            return e.compact_repr(
                context=context, use_name=use_name, no_lit_suffix=no_lit_suffix
            )

        assert False

    def __rich_repr__(self):
        """Yield values for rich text display (compact repr and full type name)."""
        try:
            yield self.compact_repr()
        except Exception as e:
            yield f"Error in repr: {e}"
        yield "on " + fabll.Traits(self).get_obj_raw().get_full_name(types=True)

    def get_depth(self) -> int:
        if expr := self.as_expression.try_get():
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
        # TODO remove in favor of the one in can_be_operand
        return self.as_operand.get().get_operations(
            types=types,
            predicates_only=predicates_only,
            recursive=recursive,
        )

    def get_obj(self) -> "fabll.Node":
        return fabll.Traits(self).get_obj_raw()

    def has_implicit_predicates_recursive(self) -> bool:
        from faebryk.library.Expressions import has_implicit_constraints

        if self.try_get_sibling_trait(has_implicit_constraints):
            return True
        if expr := self.as_expression.try_get():
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

        def format_lit(literal: "F.Literals.is_literal") -> str:
            if param := self.as_parameter.try_get():
                obj = fabll.Traits(param).get_obj_raw()
                if numeric_param := obj.try_cast(NumericParameter):
                    # Try to get the Numbers literal
                    numbers_lit = (
                        fabll.Traits(literal).get_obj_raw().try_cast(F.Literals.Numbers)
                    )
                    if numbers_lit:
                        return numeric_param.format_literal_for_display(numbers_lit)
            return literal.pretty_str()

        if lit is not None:
            out = f"{{I|{format_lit(lit)}}}"
        elif (lit := self.try_get_subset_or_alias_literal()) is not None:
            out = f"{{S|{format_lit(lit)}}}"
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
        self,
        context: "ReprContext | None" = None,
        use_name: bool = False,
        no_lit_suffix: bool = False,
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
            letter = _param_id_to_human_str(context.variable_mapping.mapping[self])

        unitstr = ""
        if numeric_param := obj.try_cast(NumericParameter):
            display_unit = numeric_param.get_display_units()
            unit_symbol = display_unit.compact_repr()
            # Don't show "dimensionless" as a unit
            if unit_symbol != "dimensionless":
                unitstr = f"[{unit_symbol}]"

        out = f"{letter}{unitstr}"
        out += (
            self.as_parameter_operatable.get()._get_lit_suffix()
            if not no_lit_suffix
            else ""
        )

        return out

    def domain_set(
        self, *, g: graph.GraphView | None = None, tg: fbrk.TypeGraph | None = None
    ) -> "F.Literals.is_literal":
        g = g or self.g
        tg = tg or self.tg
        return self.switch_cast().domain_set(g=g, tg=tg).is_literal.get()

    def switch_cast(
        self,
    ) -> "StringParameter | BooleanParameter | EnumParameter | NumericParameter":
        obj = fabll.Traits(self).get_obj_raw()
        types = [StringParameter, BooleanParameter, EnumParameter, NumericParameter]
        for t in types:
            if x := obj.try_cast(t):
                return x
        raise TypeError(f"Unknown parameter type: {obj}")


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

    def domain_set(
        self, *, g: graph.GraphView, tg: fbrk.TypeGraph
    ) -> "Literals.Strings":
        raise NotImplementedError("domain_set not implemented for StringParameter")


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

        lit = (
            Booleans.bind_typegraph_from_instance(instance=self.instance)
            .create_instance(g=g)
            .setup_from_values(value)
        )

        self.is_parameter_operatable.get().alias_to_literal(g=g, value=lit)

    def domain_set(
        self, *, g: graph.GraphView, tg: fbrk.TypeGraph
    ) -> "Literals.Booleans":
        return (
            F.Literals.Booleans.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup_from_values(True, False)
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
        return (
            fabll.Traits(self.is_parameter_operatable.get().force_extract_literal())
            .get_obj_raw()
            .cast(F.Literals.AbstractEnums, check=False)
        )

    def setup(self, enum: type[Enum]) -> Self:  # type: ignore[invalid-method-override]
        atype = F.Literals.EnumsFactory(enum)
        enum_type_node = fabll.TypeNodeBoundTG.get_or_create_type_in_tg(
            tg=self.tg, t=atype
        )
        self.enum_domain_pointer.get().point(
            fabll.Node.bind_instance(instance=enum_type_node)
        )
        return self

    def alias_to_literal(
        self, *enum_members: Enum, g: graph.GraphView | None = None
    ) -> None:
        g = g or self.instance.g()
        from faebryk.library.Literals import EnumsFactory

        enum_type = EnumsFactory(type(enum_members[0]))
        enum_type_node = fabll.TypeNodeBoundTG.get_or_create_type_in_tg(
            tg=self.tg, t=enum_type
        )
        self.enum_domain_pointer.get().point(
            fabll.Node.bind_instance(instance=enum_type_node)
        )

        lit = (
            enum_type.bind_typegraph(tg=self.tg)
            .create_instance(g=g)
            .setup(*enum_members)
        )

        self.is_parameter_operatable.get().alias_to_literal(g=g, value=lit)

    @classmethod
    def MakeChild(cls, enum_t: type[Enum]) -> fabll._ChildField[Self]:  # type: ignore[invalid-method-override]
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

    def domain_set(
        self, *, g: graph.GraphView, tg: fbrk.TypeGraph
    ) -> "Literals.AbstractEnums":
        g = g or self.g
        tg = tg or self.tg

        from faebryk.library.Literals import AbstractEnums

        enum_type_node = AbstractEnums(self.enum_domain_pointer.get().deref().instance)
        all_enum_values = AbstractEnums.get_all_members_of_enum_type(enum_type_node, tg)

        enum_lit = AbstractEnums(
            tg.instantiate_node(type_node=enum_type_node.instance, attributes={})
        )
        enum_lit.constrain_to_values(
            *[enum_value.value for enum_value in all_enum_values]
        )

        return enum_lit


class NumericParameter(fabll.Node):
    is_parameter = fabll.Traits.MakeEdge(is_parameter.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(is_parameter_operatable.MakeChild())
    can_be_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())
    number_domain = F.Collections.Pointer.MakeChild()

    class DOMAIN_SKIP:
        pass

    # domain = fabll.ChildField(NumberDomain)

    def get_units(self) -> "Units.is_unit":
        from faebryk.library.Units import has_unit

        return self.get_trait(has_unit).get_is_unit()

    def get_display_units(self) -> "Units.is_unit":
        from faebryk.library.Units import has_display_unit

        if trait := self.try_get_trait(has_display_unit):
            return trait.get_is_unit()
        return self.get_units()

    def format_literal_for_display(
        self, lit: "Literals.Numbers", show_tolerance: bool = True
    ) -> str:
        display_unit = self.get_display_units()
        converted = lit.convert_to_unit(display_unit, g=self.g, tg=self.tg)
        return converted.pretty_str(show_tolerance=show_tolerance)

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

    def alias_to_literal(
        self, g: graph.GraphView, value: "float | F.Literals.Numbers"
    ) -> None:
        match value:
            case float():
                from faebryk.library.Literals import Numbers

                lit = (
                    Numbers.bind_typegraph(tg=self.tg)
                    .create_instance(g=g)
                    .setup_from_singleton(value=value, unit=self.get_units())
                )
            case F.Literals.Numbers():
                lit = value
            case _:
                raise ValueError(f"Invalid value type: {type(value)}")

        self.is_parameter_operatable.get().alias_to_literal(g=g, value=lit)

    def setup(  # type: ignore[invalid-method-override]
        self,
        *,
        is_unit: "Units.is_unit",
        # hard constraints
        within: "Literals.Numbers | None" = None,
        domain: "NumberDomain.Args | None | type[NumericParameter.DOMAIN_SKIP]" = None,
    ) -> Self:
        from faebryk.library.Expressions import IsSubset
        from faebryk.library.NumberDomain import NumberDomain
        from faebryk.library.Units import has_display_unit, has_unit

        base_unit = is_unit.to_base_units(g=self.g, tg=self.tg)
        fabll.Traits.create_and_add_instance_to(self, has_unit).setup(is_unit=base_unit)
        fabll.Traits.create_and_add_instance_to(self, has_display_unit).setup(
            is_unit=is_unit
        )

        if within is not None:
            IsSubset.bind_typegraph(tg=self.tg).create_instance(g=self.g).setup(
                subset=self.can_be_operand.get(),
                superset=within.can_be_operand.get(),
                assert_=True,
            )
        if domain is not NumericParameter.DOMAIN_SKIP:
            assert (domain is None) or isinstance(domain, NumberDomain.Args)
            domain = domain or NumberDomain.Args()
            # TODO other domain constraints
            if not domain.negative:
                IsSubset.bind_typegraph(tg=self.tg).create_instance(g=self.g).setup(
                    subset=self.can_be_operand.get(),
                    superset=F.Literals.Numbers.bind_typegraph(tg=self.tg)
                    .create_instance(g=self.g)
                    .setup_from_min_max(
                        min=0,
                        max=math.inf,
                        unit=base_unit,
                    )
                    .can_be_operand.get(),
                    assert_=True,
                )

        return self

    @classmethod
    def MakeChild(  # type: ignore[invalid-method-override]
        cls,
        unit: type[fabll.Node],
        domain: "NumberDomain.Args | None" = None,
    ):
        from faebryk.library.Units import (
            extract_unit_info,
            has_display_unit,
            has_unit,
            is_unit,
            is_unit_type,
        )

        out = fabll._ChildField(cls)

        # Create display unit from the provided type
        display_unit_child = unit.MakeChild()
        out.add_dependant(display_unit_child)
        out.add_dependant(
            fabll.Traits.MakeEdge(
                has_display_unit.MakeChild([display_unit_child]), [out]
            )
        )

        unit_info = extract_unit_info(unit)
        if unit_info.multiplier == 1.0 and unit_info.offset == 0.0:
            # Base unit - use same child for has_unit
            out.add_dependant(
                fabll.Traits.MakeEdge(has_unit.MakeChild([display_unit_child]), [out])
            )
        else:
            is_unit_trait_child = is_unit.MakeChild(
                symbols=(),
                basis_vector=unit_info.basis_vector,
                multiplier=1.0,
                offset=0.0,
            )

            class _BaseUnit(fabll.Node):
                is_unit_type_trait = fabll.Traits.MakeEdge(
                    is_unit_type.MakeChild(())
                ).put_on_type()
                is_unit = fabll.Traits.MakeEdge(is_unit_trait_child)
                can_be_operand_trait = fabll.Traits.MakeEdge(can_be_operand.MakeChild())

            base_unit_child = _BaseUnit.MakeChild()
            out.add_dependant(base_unit_child)
            out.add_dependant(
                fabll.Traits.MakeEdge(has_unit.MakeChild([base_unit_child]), [out])
            )

        # TODO domain constraints

        return out

    def try_extract_aliased_literal(self) -> "Literals.Numbers | None":
        from faebryk.library.Expressions import Is
        from faebryk.library.Literals import Numbers

        return self.is_parameter_operatable.get().try_get_constrained_literal(
            lit_type=Numbers, pred_type=Is
        )

    def force_extract_literal(self) -> "Literals.Numbers":
        from faebryk.library.Expressions import Is
        from faebryk.library.Literals import Numbers

        return self.is_parameter_operatable.get().force_extract_literal(
            lit_type=Numbers,
            pred_type=Is,
        )

    def try_extract_aliased_literal_subset(self) -> "Literals.Numbers | None":
        from faebryk.library.Expressions import IsSubset
        from faebryk.library.Literals import Numbers

        return self.is_parameter_operatable.get().try_get_constrained_literal(
            lit_type=Numbers, pred_type=IsSubset
        )

    def force_extract_literal_subset(self) -> "Literals.Numbers":
        from faebryk.library.Expressions import IsSubset
        from faebryk.library.Literals import Numbers

        return self.is_parameter_operatable.get().force_extract_literal(
            lit_type=Numbers,
            pred_type=IsSubset,
        )

    def domain_set(
        self, *, g: graph.GraphView, tg: fbrk.TypeGraph
    ) -> "Literals.Numbers":
        return (
            F.Literals.Numbers.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup_from_min_max(
                min=-math.inf,
                max=math.inf,
                unit=self.get_units(),
            )
        )


ParameterNodes = StringParameter | BooleanParameter | EnumParameter | NumericParameter

# Binding context ----------------------------------------------------------------------


class BoundParameterContext:
    """
    Convenience context for binding parameter types and creating instances.

    Usage:
        ctx = BoundParameterContext(tg=tg, g=g)
        my_param = ctx.NumericParameter.setup(units=F .Units.Ohm)
    """

    def __init__(self, tg: fbrk.TypeGraph, g: graph.GraphView):
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

    from faebryk.library.has_usage_example import has_usage_example
    from faebryk.library.Literals import AbstractEnums, EnumsFactory

    class ExampleNode(fabll.Node):
        class MyEnum(Enum):
            A = "a"
            B = "b"
            C = "c"
            D = "d"

        enum_p_tg = EnumParameter.MakeChild(enum_t=MyEnum)
        constraint = AbstractEnums.MakeChild_ConstrainToLiteral(
            [enum_p_tg], MyEnum.B, MyEnum.C
        )

        _has_usage_example = has_usage_example.MakeChild(
            example="",
            language=has_usage_example.Language.ato,
        ).put_on_type()

    example_node = ExampleNode.bind_typegraph(tg=tg).create_instance(g=g)

    # Enum Literal Type Node
    atype = EnumsFactory(ExampleNode.MyEnum)
    cls_n = cast(type[fabll.NodeT], atype)
    _ = fabll.TypeNodeBoundTG.get_or_create_type_in_tg(tg=tg, t=cls_n)

    # Enum Parameter from TG
    enum_param = example_node.enum_p_tg.get()

    abstract_enum_type_node = AbstractEnums(enum_param.get_enum_type().instance)
    # assert abstract_enum_type_node.is_same(enum_type_node)

    assert [
        (m.name, m.value)
        for m in AbstractEnums.get_all_members_of_enum_type(
            node=abstract_enum_type_node, tg=tg
        )
    ] == [(m.name, m.value) for m in ExampleNode.MyEnum]

    assert AbstractEnums.get_enum_as_dict_for_type(
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
    from faebryk.library.Literals import Strings

    string_p = StringParameter.bind_typegraph(tg=tg).create_instance(g=g)
    string_p.alias_to_literal("IG constrained")
    assert string_p.force_extract_literal().get_values()[0] == "IG constrained"

    class ExampleStringParameter(fabll.Node):
        string_p_tg = StringParameter.MakeChild()
        constraint = Strings.MakeChild_ConstrainToLiteral(
            [string_p_tg], "TG constrained"
        )

    esp = ExampleStringParameter.bind_typegraph(tg=tg).create_instance(g=g)
    assert esp.string_p_tg.get().force_extract_literal().get_value() == "TG constrained"


def test_boolean_param():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    from faebryk.library.Literals import Booleans

    boolean_p = BooleanParameter.bind_typegraph(tg=tg).create_instance(g=g)
    boolean_p.alias_to_single(value=True, g=g)
    assert boolean_p.force_extract_literal().get_values()[0]

    class ExampleBooleanParameter(fabll.Node):
        boolean_p_tg = BooleanParameter.MakeChild()
        constraint = Booleans.MakeChild_ConstrainToLiteral([boolean_p_tg], True)

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


def test_new_definitions():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    from faebryk.library.Units import Ohm

    parameters = BoundParameterContext(tg, g)

    parameters.NumericParameter.setup(
        is_unit=Ohm.bind_typegraph(tg=tg).create_instance(g=g).is_unit.get(),
    )


def test_compact_repr():
    """
    Test compact_repr for parameters and expressions.

    This test verifies that:
    1. Parameters are assigned letters A, B, C... in order of first use
    2. Expressions are formatted with proper symbols (+, *, ≥, ¬, ∧)
    3. After exhausting A-Z, a-z, α-ω, it wraps to A₁, B₁, etc.
    """

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    from faebryk.library.Expressions import Add, And, GreaterOrEqual, Multiply, Not
    from faebryk.library.Literals import BoundLiteralContext
    from faebryk.library.Units import Dimensionless, Volt

    # Create unit instances for Volt and Dimensionless
    volt_unit = Volt.bind_typegraph(tg=tg).create_instance(g=g).is_unit.get()
    dimensionless_unit = (
        Dimensionless.bind_typegraph(tg=tg).create_instance(g=g).is_unit.get()
    )
    literals = BoundLiteralContext(tg=tg, g=g)

    # Create numeric parameters with Volt unit
    p1 = (
        NumericParameter.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup(is_unit=volt_unit)
    )
    p2 = (
        NumericParameter.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup(is_unit=volt_unit)
    )

    context = ReprContext()

    # Create literal: 5 V
    five_volt = literals.create_numbers_from_singleton(value=5.0, unit=volt_unit)

    # Create literal: 10 (dimensionless scalar)
    ten_scalar = literals.create_numbers_from_singleton(
        value=10.0, unit=dimensionless_unit
    )

    # Build expression: (p1 + p2 + 5V) * 10
    # Using .c() methods which return can_be_operand
    p1_op = p1.can_be_operand.get()
    p2_op = p2.can_be_operand.get()
    five_volt_op = five_volt.can_be_operand.get()
    ten_scalar_op = ten_scalar.can_be_operand.get()

    # (p1 + p2)
    p1_plus_p2 = Add.c(p1_op, p2_op)
    # (p1 + p2 + 5V)
    sum_with_five = Add.c(p1_plus_p2, five_volt_op)
    # ((p1 + p2 + 5V) * 10)
    expr = Multiply.c(sum_with_five, ten_scalar_op)

    # Get expression repr
    # Parameters now show their display unit in brackets, e.g., A[V] for Volts
    expr_po = expr.as_parameter_operatable.force_get()
    exprstr = expr_po.compact_repr(context, no_lit_suffix=True)
    assert exprstr == "((A[V] + B[V]) + 5.0V) * 10.0"
    exprstr_w_lit_suffix = expr_po.compact_repr(context)
    assert (
        exprstr_w_lit_suffix
        == "((A[V]{S|{0.0..∞}V} + B[V]{S|{0.0..∞}V}) + 5.0V) * 10.0"
    )

    # Test p2 + p1 (order matters in repr context - p2 was already assigned 'B')
    expr2 = Add.c(p2_op, p1_op)
    expr2_po = expr2.as_parameter_operatable.force_get()
    expr2str = expr2_po.compact_repr(context, no_lit_suffix=True)
    assert expr2str == "B[V] + A[V]"
    expr2str_w_lit_suffix = expr2_po.compact_repr(context)
    assert expr2str_w_lit_suffix == "B[V]{S|{0.0..∞}V} + A[V]{S|{0.0..∞}V}"

    # Create a boolean parameter (p3 will be 'C')
    p3 = BooleanParameter.bind_typegraph(tg=tg).create_instance(g=g)
    p3_op = p3.can_be_operand.get()

    # Create Not(p3)
    expr3 = Not.c(p3_op)
    expr3_po = expr3.as_parameter_operatable.force_get()
    expr3str = expr3_po.compact_repr(context, no_lit_suffix=True)
    assert expr3str == "¬C"
    expr3str_w_lit_suffix = expr3_po.compact_repr(context)
    assert expr3str_w_lit_suffix == "¬C"

    # Create 10 V literal for comparison
    ten_volt = literals.create_numbers_from_singleton(value=10.0, unit=volt_unit)
    ten_volt_op = ten_volt.can_be_operand.get()

    # Create expr >= 10V
    ge_expr = GreaterOrEqual.c(expr, ten_volt_op)

    # Create And(Not(p3), expr >= 10V)
    expr4 = And.c(expr3, ge_expr)
    expr4_po = expr4.as_parameter_operatable.force_get()
    expr4str = expr4_po.compact_repr(context, no_lit_suffix=True)
    assert expr4str == "¬C ∧ ((((A[V] + B[V]) + 5.0V) * 10.0) ≥ 10.0V)"
    expr4str_w_lit_suffix = expr4_po.compact_repr(context)
    assert (
        expr4str_w_lit_suffix
        == "¬C ∧ ((((A[V]{S|{0.0..∞}V} + B[V]{S|{0.0..∞}V}) + 5.0V) * 10.0) ≥ 10.0V)"
    )

    # Helper to create dimensionless numeric parameters
    def make_param():
        return (
            NumericParameter.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup(is_unit=dimensionless_unit)
        )

    # Create parameters to exhaust letters D-Y (ord("Z") - ord("C") - 1 = 22)
    # C is used by p3
    manyps = times(ord("Z") - ord("C") - 1, make_param)
    # Sum them to register in context
    if manyps:
        ops = [p.can_be_operand.get() for p in manyps]
        sum_expr = Add.c(*ops)
        sum_expr_po = sum_expr.as_parameter_operatable.force_get()
        sum_expr_po.compact_repr(context)

    # Next parameter should be 'Z'
    pZ = make_param()
    pZ_repr = pZ.is_parameter.get().compact_repr(context, no_lit_suffix=True)
    assert pZ_repr == "Z"
    pZ_repr_w_lit_suffix = pZ.is_parameter.get().compact_repr(context)
    assert pZ_repr_w_lit_suffix == "Z{S|{0.0..∞}}"

    # Next should wrap to lowercase 'a'
    pa = make_param()
    pa_repr = pa.is_parameter.get().compact_repr(context, no_lit_suffix=True)
    assert pa_repr == "a"
    pa_repr_w_lit_suffix = pa.is_parameter.get().compact_repr(context)
    assert pa_repr_w_lit_suffix == "a{S|{0.0..∞}}"

    # Create parameters b through z (ord("z") - ord("a") = 25)
    manyps2 = times(ord("z") - ord("a"), make_param)
    if manyps2:
        ops = [p.can_be_operand.get() for p in manyps2]
        sum_expr2 = Add.c(*ops)
        sum_expr2_po = sum_expr2.as_parameter_operatable.force_get()
        sum_expr2_po.compact_repr(context)

    # Next should be Greek alpha
    palpha = make_param()
    palpha_repr = palpha.is_parameter.get().compact_repr(context, no_lit_suffix=True)
    assert palpha_repr == "α"
    palpha_repr_w_lit_suffix = palpha.is_parameter.get().compact_repr(context)
    assert palpha_repr_w_lit_suffix == "α{S|{0.0..∞}}"

    pbeta = make_param()
    pbeta_repr = pbeta.is_parameter.get().compact_repr(context, no_lit_suffix=True)
    assert pbeta_repr == "β"
    pbeta_repr_w_lit_suffix = pbeta.is_parameter.get().compact_repr(context)
    assert pbeta_repr_w_lit_suffix == "β{S|{0.0..∞}}"

    # Create parameters γ through ω (ord("ω") - ord("β") = 23)
    manyps3 = times(ord("ω") - ord("β"), make_param)
    if manyps3:
        ops = [p.can_be_operand.get() for p in manyps3]
        sum_expr3 = Add.c(*ops)
        sum_expr3_po = sum_expr3.as_parameter_operatable.force_get()
        sum_expr3_po.compact_repr(context, no_lit_suffix=True)

    # After exhausting all alphabets, should wrap with subscript A₁
    pAA = make_param()
    pAA_repr = pAA.is_parameter.get().compact_repr(context, no_lit_suffix=True)
    assert pAA_repr == "A₁"
    pAA_repr_w_lit_suffix = pAA.is_parameter.get().compact_repr(context)
    assert pAA_repr_w_lit_suffix == "A₁{S|{0.0..∞}}"


@pytest.mark.xfail(reason="TODO is_congruent_to not implemeneted yet")
def test_expression_congruence():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    from faebryk.library.Expressions import Add, Is, Subtract
    from faebryk.library.Literals import (
        Booleans,
        BoundLiteralContext,
    )
    from faebryk.library.Units import Dimensionless

    parameters = BoundParameterContext(tg, g)

    p1 = parameters.NumericParameter
    p2 = parameters.NumericParameter
    p3 = parameters.NumericParameter

    assert (
        Add.bind_typegraph(tg)
        .create_instance(g)
        .setup(
            p1.is_parameter.get().as_operand.get(),
            p2.is_parameter.get().as_operand.get(),
        )
        .is_expression.get()
        .is_congruent_to(
            Add.bind_typegraph(tg)
            .create_instance(g)
            .setup(p1.can_be_operand.get(), p2.can_be_operand.get())
            .is_expression.get(),
            g=g,
            tg=tg,
        )
    )
    assert (
        Add.bind_typegraph(tg)
        .create_instance(g)
        .setup(
            p1.is_parameter.get().as_operand.get(),
            p2.is_parameter.get().as_operand.get(),
        )
        .is_expression.get()
        .is_congruent_to(
            Add.bind_typegraph(tg)
            .create_instance(g)
            .setup(p2.can_be_operand.get(), p1.can_be_operand.get())
            .is_expression.get(),
            g=g,
            tg=tg,
        )
    )

    # Create literals context
    literals = BoundLiteralContext(tg=tg, g=g)
    dimensionless = (
        Dimensionless.bind_typegraph(tg=tg).create_instance(g=g).is_unit.get()
    )

    # Test singleton literal hash equality
    zero_lit_1 = literals.create_numbers_from_singleton(value=0.0, unit=dimensionless)
    zero_lit_2 = literals.create_numbers_from_singleton(value=0.0, unit=dimensionless)
    assert hash(zero_lit_1.is_literal.get()) == hash(zero_lit_2.is_literal.get())
    assert zero_lit_1.is_literal.get() == zero_lit_2.is_literal.get()

    # Test Add congruence with singleton literals
    zero_lit = literals.create_numbers_from_singleton(value=0.0, unit=dimensionless)
    add_expr_1 = Add.from_operands(
        zero_lit.can_be_operand.get(),
        p2.can_be_operand.get(),
        p1.can_be_operand.get(),
        g=g,
        tg=tg,
    )
    add_expr_2 = Add.from_operands(
        p1.can_be_operand.get(),
        p2.can_be_operand.get(),
        zero_lit.can_be_operand.get(),
        g=g,
        tg=tg,
    )
    assert add_expr_1.is_expression.get().is_congruent_to(
        add_expr_2.is_expression.get(), g=g, tg=tg
    )

    # Test Add congruence with interval literals (allow_uncorrelated)
    interval_lit_1 = literals.create_numbers_from_interval(
        min=0.0, max=1.0, unit=dimensionless
    )
    interval_lit_2 = literals.create_numbers_from_interval(
        min=0.0, max=1.0, unit=dimensionless
    )
    add_interval_1 = Add.from_operands(interval_lit_1.can_be_operand.get(), g=g, tg=tg)
    add_interval_2 = Add.from_operands(interval_lit_2.can_be_operand.get(), g=g, tg=tg)
    assert add_interval_1.is_expression.get().is_congruent_to(
        add_interval_2.is_expression.get(), g=g, tg=tg, allow_uncorrelated=True
    )

    # Test Subtract non-congruence (order matters)
    sub_1 = Subtract.from_operands(
        p1.can_be_operand.get(), p2.can_be_operand.get(), g=g, tg=tg
    )
    sub_2 = Subtract.from_operands(
        p2.can_be_operand.get(), p1.can_be_operand.get(), g=g, tg=tg
    )
    assert not sub_1.is_expression.get().is_congruent_to(
        sub_2.is_expression.get(), g=g, tg=tg
    )

    # Test Is congruence (commutative)
    is_expr_1 = Is.from_operands(
        p1.can_be_operand.get(), p2.can_be_operand.get(), g=g, tg=tg
    )
    is_expr_2 = Is.from_operands(
        p2.can_be_operand.get(), p1.can_be_operand.get(), g=g, tg=tg
    )
    assert is_expr_1.is_expression.get().is_congruent_to(
        is_expr_2.is_expression.get(), g=g, tg=tg
    )

    # Test Is congruence with boolean literal
    bool_true = Booleans.bind_typegraph(tg=tg).create_instance(
        g=g, attributes=BooleansAttributes(True, False)
    )
    is_bool_1 = Is.from_operands(
        p1.can_be_operand.get(), bool_true.can_be_operand.get(), g=g, tg=tg
    )
    is_bool_2 = Is.from_operands(
        bool_true.can_be_operand.get(), p1.can_be_operand.get(), g=g, tg=tg
    )
    assert is_bool_1.is_expression.get().is_congruent_to(
        is_bool_2.is_expression.get(), g=g, tg=tg
    )

    # Test Is non-congruence when aliased (p3 aliased to p2)
    Is.from_operands(
        p3.can_be_operand.get(), p2.can_be_operand.get(), g=g, tg=tg, assert_=True
    )
    is_p1_p3 = Is.from_operands(
        p1.can_be_operand.get(), p3.can_be_operand.get(), g=g, tg=tg
    )
    is_p1_p2 = Is.from_operands(
        p1.can_be_operand.get(), p2.can_be_operand.get(), g=g, tg=tg
    )
    assert not is_p1_p3.is_expression.get().is_congruent_to(
        is_p1_p2.is_expression.get(), g=g, tg=tg
    )


@pytest.mark.xfail(reason="TODO is_congruent_to not implemeneted yet")
def test_expression_congruence_not():
    """Test congruence with Not expressions and enum literals."""
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    from faebryk.library.Expressions import Is, Not
    from faebryk.library.LED import LED
    from faebryk.library.Literals import AbstractEnums

    # Create an enum parameter
    A = EnumParameter.bind_typegraph(tg=tg).create_instance(g=g)

    # Create enum literal for LED.Color.EMERALD
    enum_lit_1 = (
        AbstractEnums.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup(LED.Color.EMERALD)
    )
    enum_lit_2 = (
        AbstractEnums.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup(LED.Color.EMERALD)
    )

    # Create Is(A, EMERALD) expressions
    x = Is.from_operands(
        A.can_be_operand.get(), enum_lit_1.can_be_operand.get(), g=g, tg=tg
    )
    x2 = Is.from_operands(
        A.can_be_operand.get(), enum_lit_2.can_be_operand.get(), g=g, tg=tg
    )
    assert x.is_expression.get().is_congruent_to(x2.is_expression.get(), g=g, tg=tg)

    # Create Not(x) expressions and check congruence
    not_x = Not.from_operands(x.can_be_operand.get(), g=g, tg=tg)
    not_x2 = Not.from_operands(x.can_be_operand.get(), g=g, tg=tg)
    assert not_x.is_expression.get().is_congruent_to(
        not_x2.is_expression.get(), g=g, tg=tg
    )


def test_enum_param_domain_set():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class MyEnum(Enum):
        A = "a"
        B = "b"
        C = "c"
        D = "d"

    A = EnumParameter.bind_typegraph(tg=tg).create_instance(g=g).setup(MyEnum)
    assert A.domain_set(g=g, tg=tg).is_literal.get()
    assert A.domain_set(g=g, tg=tg).get_values().sort() == ["a", "b", "c", "d"].sort()


def test_can_be_operand_pretty_print():
    from faebryk.library.Units import Ohm

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    ohm_is_unit = Ohm.bind_typegraph(tg=tg).create_instance(g=g).is_unit.get()

    singleton = (
        F.Literals.Numbers.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_singleton(value=5.0, unit=ohm_is_unit)
    )
    discrete_set = (
        F.Literals.Numbers.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_singletons(values=[1, 2, 3, 4], unit=ohm_is_unit)
    )
    continuous_set_rel = (
        F.Literals.Numbers.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_center_rel(center=5.0, rel=0.005, unit=ohm_is_unit)
    )
    continuous_set = (
        F.Literals.Numbers.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_min_max(min=5.0, max=10.0, unit=ohm_is_unit)
    )
    inf_set = (
        F.Literals.Numbers.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_min_max(min=-math.inf, max=math.inf, unit=ohm_is_unit)
    )
    another_continuous_set = (
        F.Literals.Numbers.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_min_max(min=15.0, max=20.0, unit=ohm_is_unit)
    )
    disjoint_union = F.Literals.Numbers.op_union_interval(
        continuous_set,
        another_continuous_set,
        g=g,
        tg=tg,
    )

    assert singleton.can_be_operand.get().pretty() == "5.0Ω"
    assert discrete_set.can_be_operand.get().pretty() == "{1.0, 2.0, 3.0, 4.0}Ω"
    assert continuous_set.can_be_operand.get().pretty() == "{5.0..10.0}Ω"
    assert inf_set.can_be_operand.get().pretty() == "{-∞..∞}Ω"
    assert continuous_set_rel.can_be_operand.get().pretty() == "{5.0±0.5%}Ω"
    assert disjoint_union.can_be_operand.get().pretty() == "{5.0..10.0, 15.0..20.0}Ω"


def test_is_discrete_set():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    from faebryk.library.Units import Dimensionless

    dl_is_unit = Dimensionless.bind_typegraph(tg=tg).create_instance(g=g).is_unit.get()
    discrete_set = (
        F.Literals.Numbers.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_singletons(values=[1, 2, 3, 4], unit=dl_is_unit)
    )
    assert discrete_set.get_numeric_set().is_discrete_set()

    continuous_set = (
        F.Literals.Numbers.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_min_max(min=0, max=10, unit=dl_is_unit)
    )
    assert not continuous_set.get_numeric_set().is_discrete_set()


def test_copy_into_enum_parameter():
    """
    Test copying an enum parameter to another graph preserves the enum type.

    The issue: When we copy just the parameter, the `Is` expression that constrains
    it doesn't get copied because:
    - `Is` expression has operand edges pointing TO the parameter (not from)
    - copy_into traverses forward from the node being copied

    This test demonstrates that copying the Is expression (which contains the
    constraint) works, while copying just the parameter loses the constraint.
    """
    # TODO WIP, written by llm
    # supposed to debug param copying in mutator.mutate_parameter

    from enum import Enum

    g1 = fabll.graph.GraphView.create()
    tg1 = fbrk.TypeGraph.create(g=g1)

    class MyEnum(Enum):
        A = "a"
        B = "b"
        C = "c"

    # Create enum parameter and set up with the enum type
    enum_param = EnumParameter.bind_typegraph(tg=tg1).create_instance(g=g1)
    enum_param.setup(enum=MyEnum)

    # Alias to a specific value - this creates an Is expression
    enum_param.alias_to_literal(MyEnum.A, MyEnum.B, g=g1)

    # Verify original works
    original_lit = enum_param.force_extract_literal()
    original_values = original_lit.get_values()
    assert sorted(original_values) == ["a", "b"]

    # Get the Is expression that constrains the parameter
    original_ops = enum_param.is_parameter_operatable.get().get_operations()
    assert len(original_ops) == 1, f"Expected 1 operation, got {len(original_ops)}"
    is_expr = list(original_ops)[0]
    print(f"\nOriginal Is expression: {is_expr}")

    # Create new graph and copy the TypeGraph first
    g2 = graph.GraphView.create()
    tg2 = tg1.copy_into(target_graph=g2, minimal=False)

    # Copy the Is expression (not just the parameter)
    # This should copy both operands (parameter and literal) along with it
    copied_is = is_expr.copy_into(g=g2)
    print(f"Copied Is expression in g2: {copied_is}")

    # The copied parameter should now be accessible via the copied Is expression's operands
    # Get operands using the is_expression trait API
    from faebryk.library.Expressions import is_expression

    copied_is_expr_trait = copied_is.get_trait(is_expression)
    copied_operands = copied_is_expr_trait.get_operands()
    print(f"Copied operands: {copied_operands}")

    # Find the copied enum parameter
    copied_param = None
    for operand in copied_operands:
        po = operand.as_parameter_operatable.try_get()
        if po:
            param_trait = po.as_parameter.try_get()
            if param_trait:
                copied_param = fabll.Traits(param_trait).get_obj(EnumParameter)
                break

    assert copied_param is not None, "Could not find copied enum parameter"
    print(f"Copied enum parameter: {copied_param}")

    # Verify the copied parameter has same constrained literal
    copied_ops = copied_param.is_parameter_operatable.get().get_operations()
    print(f"Copied parameter has {len(copied_ops)} operations")
    assert len(copied_ops) == 1, f"Expected 1 operation, got {len(copied_ops)}"

    copied_lit = copied_param.force_extract_literal()
    copied_values = copied_lit.get_values()
    assert sorted(copied_values) == ["a", "b"], (
        f"Expected ['a', 'b'] but got {copied_values}"
    )

    # Verify we can still read the original
    assert sorted(enum_param.force_extract_literal().get_values()) == ["a", "b"]

    # Verify the enum type can still be accessed
    copied_enum_type = copied_param.get_enum_type()
    assert copied_enum_type is not None


def test_copy_numeric_parameter():
    from faebryk.library.Units import Dimensionless

    g1 = fabll.graph.GraphView.create()
    tg1 = fbrk.TypeGraph.create(g=g1)

    class App(fabll.Node):
        numeric_param = NumericParameter.MakeChild(unit=Dimensionless)

    app = App.bind_typegraph(tg=tg1).create_instance(g=g1)

    # numeric_param = NumericParameter.bind_typegraph(tg=tg1).create_instance(g=g1)
    # numeric_param.setup(is_unit=dl_is_unit)
    numeric_param = app.numeric_param.get()

    g2 = graph.GraphView.create()
    numeric_param2 = numeric_param.copy_into(g=g2)

    numeric_param.debug_print_tree()
    numeric_param2.debug_print_tree()


def test_display_unit_normalization():
    """
    Test that parameters normalize to base units internally while
    preserving the display unit for output.
    """
    from faebryk.library.Units import Volt, decode_symbol_runtime

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    # Create a Volt instance to register it in the typegraph
    _ = Volt.bind_typegraph(tg=tg).create_instance(g=g)

    # Get mV unit (millivolt) via decode_symbol_runtime
    mv_unit = decode_symbol_runtime(g=g, tg=tg, symbol="mV")

    # Verify mV has the correct multiplier
    assert mv_unit._extract_multiplier() == 0.001

    # Create a numeric parameter with mV as display unit
    param = NumericParameter.bind_typegraph(tg=tg).create_instance(g=g)
    param.setup(is_unit=mv_unit)

    # The has_unit trait should store the base unit (V, multiplier=1)
    base_unit = param.get_units()
    assert base_unit._extract_multiplier() == 1.0

    # The has_display_unit trait should store mV (multiplier=0.001)
    display_unit = param.get_display_units()
    assert display_unit._extract_multiplier() == 0.001


def test_display_unit_compact_repr():
    """
    Test that compact_repr shows the display unit.

    Note: Anonymous units (from decode_symbol_runtime) don't preserve symbols,
    so the display shows basis vector notation. Named units (like Volt) show
    their symbol.
    """
    from faebryk.library.Units import Volt

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    # Create a Volt instance
    volt_instance = Volt.bind_typegraph(tg=tg).create_instance(g=g)
    volt_unit = volt_instance.is_unit.get()

    # Create a numeric parameter with V as display unit
    param = NumericParameter.bind_typegraph(tg=tg).create_instance(g=g)
    param.setup(is_unit=volt_unit)

    # Get the is_parameter trait
    is_param = param.is_parameter.get()

    # compact_repr should include the display unit symbol
    context = ReprContext()
    repr_str = is_param.compact_repr(context=context, no_lit_suffix=True)

    # Should show [V] for Volt display unit
    assert "[V]" in repr_str


def test_display_unit_literal_conversion():
    from faebryk.library.Literals import Numbers
    from faebryk.library.Units import Volt, decode_symbol_runtime

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    # Create a Volt instance to register it
    volt_instance = Volt.bind_typegraph(tg=tg).create_instance(g=g)
    volt_unit = volt_instance.is_unit.get()

    # Get mV unit
    mv_unit = decode_symbol_runtime(g=g, tg=tg, symbol="mV")

    # Create a numeric parameter with mV as display unit
    param = NumericParameter.bind_typegraph(tg=tg).create_instance(g=g)
    param.setup(is_unit=mv_unit)

    # Create a literal in base units (Volts): 4-5 V
    literal = (
        Numbers.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_min_max(min=4.0, max=5.0, unit=volt_unit)
    )

    # Alias the parameter to the literal
    param.alias_to_literal(g=g, value=literal)

    # Format the literal using the parameter's display unit
    formatted = param.format_literal_for_display(literal)

    # Should show values converted to mV (4000-5000)
    # The key test is VALUE conversion from V to mV
    assert "4000" in formatted
    assert "5000" in formatted


def test_display_unit_fallback():
    from faebryk.library.Units import Volt

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    # Create a Volt instance
    volt_instance = Volt.bind_typegraph(tg=tg).create_instance(g=g)
    volt_unit = volt_instance.is_unit.get()

    # Create a numeric parameter with base unit (V)
    # When using base unit, has_unit and has_display_unit should be the same
    param = NumericParameter.bind_typegraph(tg=tg).create_instance(g=g)
    param.setup(is_unit=volt_unit)

    # Both should return the same unit (V with multiplier=1)
    base_unit = param.get_units()
    display_unit = param.get_display_units()

    assert base_unit._extract_multiplier() == 1.0
    assert display_unit._extract_multiplier() == 1.0


def test_display_unit_makechild():
    from faebryk.library.Units import Ohm, has_display_unit, has_unit

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class TestModule(fabll.Node):
        resistance = NumericParameter.MakeChild(unit=Ohm)

    module = TestModule.bind_typegraph(tg=tg).create_instance(g=g)
    param = module.resistance.get()

    # Both traits should be present
    assert param.has_trait(has_unit)
    assert param.has_trait(has_display_unit)

    # Both should point to Ohm (base unit)
    base_unit = param.get_units()
    display_unit = param.get_display_units()

    # For MakeChild with base unit type, both should have multiplier=1
    assert base_unit._extract_multiplier() == 1.0
    assert display_unit._extract_multiplier() == 1.0


def test_display_unit_lit_suffix_conversion():
    from faebryk.library.Literals import Numbers
    from faebryk.library.Units import Volt, decode_symbol_runtime

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    # Create a Volt instance
    volt_instance = Volt.bind_typegraph(tg=tg).create_instance(g=g)
    volt_unit = volt_instance.is_unit.get()

    # Get mV unit
    mv_unit = decode_symbol_runtime(g=g, tg=tg, symbol="mV")

    # Create a numeric parameter with mV as display unit
    param = NumericParameter.bind_typegraph(tg=tg).create_instance(g=g)
    param.setup(is_unit=mv_unit)

    # Create a literal in base units (Volts): 5 V (singleton)
    literal = (
        Numbers.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_singleton(value=5.0, unit=volt_unit)
    )

    # Alias the parameter to the literal
    param.alias_to_literal(g=g, value=literal)

    # Get the compact repr with lit suffix
    is_param = param.is_parameter.get()
    context = ReprContext()
    repr_str = is_param.compact_repr(context=context)

    # The value should be converted to display units (5V = 5000mV)
    assert "5000" in repr_str
    # Note: decode_symbol_runtime creates anonymous units without symbol preservation
    # The basis vector representation is used instead of "mV"


if __name__ == "__main__":
    import typer

    typer.run(test_can_be_operand_pretty_print)
