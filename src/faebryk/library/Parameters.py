import math
from enum import Enum
from typing import TYPE_CHECKING, Self, cast

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import KeyErrorAmbiguous, not_none, once

if TYPE_CHECKING:
    import faebryk.library.Literals as Literals
    import faebryk.library.Units as Units
    from faebryk.library.NumberDomain import NumberDomain


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

    def get_obj_raw(self) -> fabll.Node:
        return fabll.Traits(self).get_obj_raw()

    def pretty(
        self,
        use_name: bool = True,
        no_lit_suffix: bool = False,
    ) -> str:
        """Return context-aware string (pretty_str for literals, compact_repr else)."""
        if lit := self.as_literal.try_get():
            return lit.pretty_str()
        if po := self.as_parameter_operatable.try_get():
            return po.compact_repr(use_full_name=use_name, no_lit_suffix=no_lit_suffix)
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

    def get_depth(self) -> float:
        """
        Returns depth of the operand in an expression tree.

        - Literals: 0
        - Parameters: 0.05
        - Expressions: 1 + max(operand depths)
        """
        if self.as_literal.try_get():
            return 0
        if po := self.as_parameter_operatable.try_get():
            if expr := po.as_expression.try_get():
                return expr.get_depth()
            # It's a parameter (not an expression)
            return 0.05
        # Fallback
        return 0

    def get_root_operands(
        self, *more: "can_be_operand", predicates_only: bool = False
    ) -> set["can_be_operand"]:
        # Import inside function to avoid gen_F.py cycle detection
        from faebryk.library.Expressions import is_expression, is_predicate

        expr_leaves = set((self, *more))

        for e in set(expr_leaves):
            if expr := e.try_get_sibling_trait(is_expression):
                expr_leaves.update(expr.get_operand_leaves())

        all_expressions = {
            expr.get_trait(can_be_operand)
            for leaf in expr_leaves
            for expr in leaf.get_operations(recursive=True, predicates_only=False)
            if not predicates_only or expr.has_trait(is_predicate)
        }

        root_expressions = {
            root_expr
            for root_expr in all_expressions
            if not root_expr.get_operations(predicates_only=predicates_only)
        }

        return root_expressions

    def __rich_repr__(self):
        """Yield values for rich text display (compact repr and full type name)."""
        try:
            yield self.pretty()
        except Exception as e:
            yield f"Error in repr: {e}"
        yield "on " + fabll.Traits(self).get_obj_raw().get_full_name(types=True)


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

    def compact_repr(
        self,
        use_full_name: bool = False,
        no_lit_suffix: bool = False,
        no_class_suffix: bool = False,
    ) -> str:
        """Return compact math representation (delegates to parameter or expression)."""
        if p := self.as_parameter.try_get():
            return p.compact_repr(
                use_full_name=use_full_name,
                no_lit_suffix=no_lit_suffix,
            )
        if e := self.as_expression.try_get():
            return e.compact_repr(
                use_full_name=use_full_name,
                no_lit_suffix=no_lit_suffix,
                no_class_suffix=no_class_suffix,
            )

        assert False

    def __rich_repr__(self):
        """Yield values for rich text display (compact repr and full type name)."""
        try:
            yield self.compact_repr()
        except Exception as e:
            yield f"Error in repr: {e}"
        yield "on " + fabll.Traits(self).get_obj_raw().get_full_name(types=True)

    def get_depth(self) -> float:
        return self.as_operand.get().get_depth()

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

    def set_superset(self, g: graph.GraphView, value: "Literals.LiteralNodes") -> None:
        node = self.instance
        tg = not_none(fbrk.TypeGraph.of_instance(instance_node=node))
        from faebryk.library.Expressions import IsSubset

        IsSubset.bind_typegraph(tg=tg).create_instance(g=g).setup(
            self.as_operand.get(),
            value.is_literal.get().as_operand.get(),
            assert_=True,
        )

    def set_subset(self, g: graph.GraphView, value: "Literals.LiteralNodes") -> None:
        node = self.instance
        tg = not_none(fbrk.TypeGraph.of_instance(instance_node=node))
        from faebryk.library.Expressions import IsSuperset

        IsSuperset.bind_typegraph(tg=tg).create_instance(g=g).setup(
            self.as_operand.get(),
            value.is_literal.get().as_operand.get(),
            assert_=True,
        )

    # literal extraction ---------------------------------------------------------------
    def _try_extract_set[T: "fabll.NodeT" = "Literals.is_literal"](
        self,
        superset: bool,
        lit_type: type[T] | None = None,
    ) -> T | None:
        from faebryk.library.Expressions import IsSubset, IsSuperset
        from faebryk.library.Literals import is_literal

        l_op, r_op = (IsSubset, IsSuperset) if superset else (IsSuperset, IsSubset)

        lits = []
        for expr in self.get_operations(types=l_op, predicates_only=True):
            ops = expr.is_expression.get().get_operands()
            if not ops[0].is_same(self.as_operand.get()):
                continue
            for op in ops[1:]:
                if lit := op.as_literal.try_get():
                    lits.append(lit)
        for expr in self.get_operations(types=r_op, predicates_only=True):
            ops = expr.is_expression.get().get_operands()
            op = ops[0]
            if lit := op.as_literal.try_get():
                lits.append(lit)

        if not lits:
            return None
        lit_merged = F.Literals.is_literal.op_setic_intersect(*lits)

        if lit_type is None or lit_type is is_literal:
            return cast(T, lit_merged)
        return fabll.Traits(lit_merged).get_obj(lit_type)

    # new
    def try_extract_superset[T: "Literals.LiteralNodes"](
        self, lit_type: type[T] | None = None
    ) -> T | None:
        return self._try_extract_set(lit_type=lit_type, superset=True)

    def force_extract_superset[T: "Literals.LiteralNodes"](
        self, lit_type: type[T] | None = None
    ) -> T:
        lit = self.try_extract_superset(lit_type=lit_type)
        if lit is None:
            raise ParameterIsNotConstrainedToLiteral(parameter=self)
        return lit

    def try_extract_subset[T: "Literals.LiteralNodes"](
        self, lit_type: type[T] | None = None
    ) -> T | None:
        return self._try_extract_set(lit_type=lit_type, superset=False)

    def force_extract_subset[T: "Literals.LiteralNodes"](
        self, lit_type: type[T] | None = None
    ) -> T:
        lit = self.try_extract_subset(lit_type=lit_type)
        if lit is None:
            raise ParameterIsNotConstrainedToLiteral(parameter=self)
        return lit

    def _get_lit_suffix(self) -> str:
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

        try:
            subset = self.try_extract_subset()
        except KeyErrorAmbiguous as e:
            return f"{{AMBIGUOUS ⊇: {e.duplicates}}}"
        try:
            superset = self.try_extract_superset()
        except KeyErrorAmbiguous as e:
            return f"{{AMBIGUOUS ⊆: {e.duplicates}}}"

        if subset is not None and superset is not None:
            if subset.op_setic_equals(superset):
                if subset.op_setic_equals_singleton(True):
                    return "✓"
                elif subset.op_setic_equals_singleton(False):
                    return "✗"
                return f"{{⊆⊇|{format_lit(subset)}}}"

        superset_str = ""
        if superset is not None:
            formatted = format_lit(superset)
            if "{ℝ+}" in formatted:
                # careful drops unit, but unit is included in param anyway
                superset_str = "⁺"
            else:
                superset_str = f"{{⊆|{formatted}}}"

        subset_str = ""
        if subset is not None:
            subset_str = f"{{⊇|{format_lit(subset)}}}"

        return f"{subset_str}{superset_str}"


class is_parameter(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    as_parameter_operatable = fabll.Traits.ImpliedTrait(is_parameter_operatable)
    as_operand = fabll.Traits.ImpliedTrait(can_be_operand)

    def compact_repr(
        self,
        use_full_name: bool = False,
        no_lit_suffix: bool = False,
        with_detail: bool = True,
    ) -> str:
        """
        Unit only printed if not dimensionless.
        """

        obj = fabll.Traits(self).get_obj_raw()

        name = (
            obj.get_full_name()
            if use_full_name and obj.get_parent() is not None
            else obj.get_name(with_detail=with_detail)
        )

        unitstr = ""
        if numeric_param := obj.try_cast(NumericParameter):
            if (
                display_unit := numeric_param.try_get_display_units()
            ) is not None and not display_unit.is_dimensionless():
                unit_symbol = display_unit.compact_repr()
                unitstr = f"[{unit_symbol}]"

        out = f"{name}{unitstr}"
        out += (
            self.as_parameter_operatable.get()._get_lit_suffix()
            if not no_lit_suffix
            else ""
        )

        from faebryk.core.solver.mutator import is_irrelevant, is_relevant

        relevant = ""
        if self.try_get_sibling_trait(is_relevant):
            relevant = "★"
        elif self.try_get_sibling_trait(is_irrelevant):
            relevant = "⊘"
        out += relevant

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

    def set_name(self, name: str, detail: str | None = None) -> None:
        from faebryk.library.has_name_override import has_name_override

        obj = fabll.Traits(self).get_obj_raw()
        has_name = (
            has_name_override.bind_typegraph(tg=self.tg)
            .create_instance(g=self.g)
            .setup(name=name, detail=detail)
        )
        fabll.Traits.add_instance_to(node=obj, trait_instance=has_name)

    def __rich_repr__(self):
        try:
            yield self.compact_repr(no_lit_suffix=True)
        except Exception as e:
            yield f"Error in repr: {e}"
        yield "on " + fabll.Traits(self).get_obj_raw().get_full_name(types=True)


class ParameterIsNotConstrainedToLiteral(Exception):
    def __init__(self, parameter: fabll.Node):
        self.parameter = parameter


# --------------------------------------------------------------------------------------


class StringParameter(fabll.Node):
    is_parameter = fabll.Traits.MakeEdge(is_parameter.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(is_parameter_operatable.MakeChild())
    can_be_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())

    def try_extract_superset(self) -> "Literals.Strings | None":
        from faebryk.library.Literals import Strings

        return self.is_parameter_operatable.get().try_extract_superset(lit_type=Strings)

    def force_extract_superset(self) -> "Literals.Strings":
        from faebryk.library.Literals import Strings

        return self.is_parameter_operatable.get().force_extract_superset(
            lit_type=Strings
        )

    def extract_singleton(self) -> str:
        return self.force_extract_superset().get_single()

    def try_extract_singleton(self) -> str | None:
        lit = self.try_extract_superset()
        if lit is None:
            return None
        if not lit.is_singleton():
            return None
        return lit.get_single()

    # TODO get rid of this and replace with superset_to_literal
    def set_singleton(self, value: str, g: graph.GraphView | None = None) -> None:
        return self.set_superset(value, g=g)

    def set_superset(self, *values: str, g: graph.GraphView | None = None) -> None:
        g = g or self.instance.g()
        from faebryk.library.Literals import Strings

        self.is_parameter_operatable.get().set_superset(
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

    def try_extract_superset(self) -> "Literals.Booleans | None":
        from faebryk.library.Literals import Booleans

        return self.is_parameter_operatable.get().try_extract_superset(
            lit_type=Booleans
        )

    def force_extract_superset(self) -> "Literals.Booleans":
        from faebryk.library.Literals import Booleans

        return self.is_parameter_operatable.get().force_extract_superset(
            lit_type=Booleans
        )

    def force_extract_singleton(self) -> bool:
        return self.force_extract_superset().get_single()

    def try_extract_singleton(self) -> bool | None:
        lit = self.try_extract_superset()
        if lit is None:
            return None
        if not lit.is_singleton():
            return None
        return lit.get_single()

    def set_singleton(self, value: bool, g: graph.GraphView | None = None) -> None:
        g = g or self.instance.g()
        from faebryk.library.Literals import Booleans

        lit = (
            Booleans.bind_typegraph_from_instance(instance=self.instance)
            .create_instance(g=g)
            .setup_from_values(value)
        )

        self.is_parameter_operatable.get().set_superset(g=g, value=lit)

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

    def try_extract_superset[T: "F.Literals.AbstractEnums"](
        self,
    ) -> "F.Literals.AbstractEnums | None":
        if (
            result := self.is_parameter_operatable.get().try_extract_superset(
                lit_type=F.Literals.AbstractEnums
            )
        ) is not None:
            return result
        return self.domain_set(g=self.g, tg=self.tg)

    def force_extract_superset(self) -> "F.Literals.AbstractEnums":
        return (
            fabll.Traits(self.is_parameter_operatable.get().force_extract_superset())
            .get_obj_raw()
            .cast(F.Literals.AbstractEnums, check=False)
        )

    def force_extract_singleton(self) -> str:
        return self.force_extract_superset().get_single()

    def force_extract_singleton_typed[T: Enum](self, enum_type: type[T]) -> T:
        return self.force_extract_superset().get_single_value_typed(enum_type)

    def try_extract_singleton_typed[T: Enum](self, enum_type: type[T]) -> T | None:
        lit = self.try_extract_superset()
        if lit is None:
            return None
        if not lit.is_singleton():
            return None
        return lit.get_single_value_typed(enum_type)

    def setup(self, enum: type[Enum]) -> Self:  # type: ignore[invalid-method-override]
        atype = F.Literals.EnumsFactory(enum)
        enum_type_node = fabll.TypeNodeBoundTG.get_or_create_type_in_tg(
            tg=self.tg, t=atype
        )
        self.enum_domain_pointer.get().point(
            fabll.Node.bind_instance(instance=enum_type_node)
        )
        return self

    def set_superset(
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

        self.is_parameter_operatable.get().set_superset(g=g, value=lit)

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
                    identifier="enum_domain_pointer", index=None
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
        enum_lit.set_superset(*[enum_value.value for enum_value in all_enum_values])

        return enum_lit


class waits_for_unit(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    def is_resolved(self) -> bool:
        return self.try_get_sibling_trait(has_received_unit) is not None

    def resolve(self):
        obj = fabll.Traits(self).get_obj(NumericParameter)
        fabll.Traits.create_and_add_instance_to(obj, has_received_unit)


class has_received_unit(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())


class NumericParameter(fabll.Node):
    is_parameter = fabll.Traits.MakeEdge(is_parameter.MakeChild())
    is_parameter_operatable = fabll.Traits.MakeEdge(is_parameter_operatable.MakeChild())
    can_be_operand = fabll.Traits.MakeEdge(can_be_operand.MakeChild())
    number_domain = F.Collections.Pointer.MakeChild()

    class DOMAIN_SKIP:
        pass

    # domain = fabll.ChildField(NumberDomain)

    def force_get_units(self) -> "Units.is_unit":
        from faebryk.library.Units import has_unit

        return self.get_trait(has_unit).get_is_unit()

    def try_get_units(self) -> "Units.is_unit | None":
        from faebryk.library.Units import has_unit

        out = self.try_get_trait(has_unit)
        if out is None:
            return None
        return out.get_is_unit()

    def force_get_display_units(self) -> "Units.is_unit":
        from faebryk.library.Units import has_display_unit

        if trait := self.try_get_trait(has_display_unit):
            return trait.get_is_unit()
        return self.force_get_units()

    def try_get_display_units(self) -> "Units.is_unit | None":
        from faebryk.library.Units import has_display_unit

        if out := self.try_get_trait(has_display_unit):
            return out.get_is_unit()
        return self.try_get_units()

    def format_literal_for_display(
        self,
        lit: "Literals.Numbers",
        show_tolerance: bool = True,
        force_center: bool = False,
    ) -> str:
        display_unit = self.try_get_display_units()
        converted = lit.convert_to_unit(display_unit, g=self.g, tg=self.tg)
        return converted.pretty_str(
            show_tolerance=show_tolerance, force_center=force_center
        )

    def get_values(self) -> list[float]:
        """
        Return values from extracted literal subset in the parameter's display units.
        """
        return (
            self.force_extract_superset()
            .convert_to_unit(self.force_get_display_units(), g=self.g, tg=self.tg)
            .get_values()
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

    def set_superset(
        self, g: graph.GraphView, value: "float | F.Literals.Numbers"
    ) -> None:
        match value:
            case float():
                from faebryk.library.Literals import Numbers

                lit = (
                    Numbers.bind_typegraph(tg=self.tg)
                    .create_instance(g=g)
                    .setup_from_singleton(value=value, unit=self.try_get_units())
                )
            case F.Literals.Numbers():
                lit = value
            case _:
                raise ValueError(f"Invalid value type: {type(value)}")

        self.is_parameter_operatable.get().set_superset(g=g, value=lit)

    def setup(  # type: ignore[invalid-method-override]
        self,
        *,
        is_unit: "Units.is_unit | None" = None,
        # hard constraints
        within: "Literals.Numbers | None" = None,
        domain: "NumberDomain.Args | None | type[NumericParameter.DOMAIN_SKIP]" = None,
    ) -> Self:
        from faebryk.library.Expressions import IsSubset
        from faebryk.library.NumberDomain import NumberDomain
        from faebryk.library.Units import has_display_unit, has_unit

        base_unit = None
        if is_unit is not None and not is_unit.is_dimensionless():
            base_unit = is_unit.to_base_units(g=self.g, tg=self.tg)
            if base_unit:
                fabll.Traits.create_and_add_instance_to(self, has_unit).setup(
                    is_unit=base_unit
                )
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
    def MakeChild_DeferredUnit(cls) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(fabll.Traits.MakeEdge(waits_for_unit.MakeChild(), [out]))
        return out

    @staticmethod
    @once
    def _make_1_0_unit(basis_vector: "F.Units.BasisVector") -> type[fabll.Node]:
        from faebryk.library.Units import is_unit, is_unit_type

        is_unit_trait_child = is_unit.MakeChild(
            symbols=(),
            basis_vector=basis_vector,
            multiplier=1.0,
            offset=0.0,
        )

        class _BaseUnit(fabll.Node):
            _override_type_identifier = f"BaseUnit<{basis_vector}>"
            is_unit_type_trait = fabll.Traits.MakeEdge(
                is_unit_type.MakeChild(())
            ).put_on_type()
            is_unit = fabll.Traits.MakeEdge(is_unit_trait_child)
            can_be_operand_trait = fabll.Traits.MakeEdge(can_be_operand.MakeChild())

        return _BaseUnit

    @classmethod
    def MakeChild(  # type: ignore[invalid-method-override]
        cls,
        unit: type[fabll.Node] | None = None,
        domain: "NumberDomain.Args | None" = None,
    ):
        from faebryk.library.NumberDomain import NumberDomain
        from faebryk.library.Units import (
            Dimensionless,
            extract_unit_info,
            has_display_unit,
            has_unit,
        )

        if unit is Dimensionless:
            unit = None

        out = fabll._ChildField(cls)

        if unit is not None:
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
                    fabll.Traits.MakeEdge(
                        has_unit.MakeChild([display_unit_child]), [out]
                    )
                )
            else:
                base_unit_child = NumericParameter._make_1_0_unit(
                    unit_info.basis_vector
                ).MakeChild()
                out.add_dependant(base_unit_child)
                out.add_dependant(
                    fabll.Traits.MakeEdge(has_unit.MakeChild([base_unit_child]), [out])
                )

        if domain is not NumericParameter.DOMAIN_SKIP:
            assert (domain is None) or isinstance(domain, NumberDomain.Args)
            domain = domain or NumberDomain.Args()
            # TODO other domain constraints
            if not domain.negative:
                out.add_dependant(
                    F.Literals.Numbers.MakeChild_SetSuperset(
                        param_ref=[out], min=0, max=math.inf, unit=unit
                    )
                )

        return out

    def try_extract_subset(self) -> "Literals.Numbers | None":
        from faebryk.library.Literals import Numbers

        return self.is_parameter_operatable.get().try_extract_subset(lit_type=Numbers)

    def force_extract_subset(self) -> "Literals.Numbers":
        from faebryk.library.Literals import Numbers

        return self.is_parameter_operatable.get().force_extract_subset(lit_type=Numbers)

    def try_extract_superset(self) -> "Literals.Numbers | None":
        from faebryk.library.Literals import Numbers

        return self.is_parameter_operatable.get().try_extract_superset(lit_type=Numbers)

    def force_extract_superset(self) -> "Literals.Numbers":
        from faebryk.library.Literals import Numbers

        return self.is_parameter_operatable.get().force_extract_superset(
            lit_type=Numbers
        )

    def try_extract_singleton(self) -> float | None:
        lit = self.try_extract_subset()
        if lit is None:
            return None
        if not lit.is_singleton():
            return None
        return lit.get_single()

    def domain_set(
        self, *, g: graph.GraphView, tg: fbrk.TypeGraph
    ) -> "Literals.Numbers":
        return (
            F.Literals.Numbers.bind_typegraph(tg=tg)
            .create_instance(g=g)
            .setup_from_min_max(
                min=-math.inf,
                max=math.inf,
                unit=self.try_get_units(),
            )
        )

    @staticmethod
    def infer_units_in_tree(root: fabll.Node) -> None:
        """
        Resolve units for NumericParameters without has_unit trait.

        Traverses all NumericParameter instances under root, finds those missing
        the has_unit trait, resolves their unit from constraining expressions,
        and attaches the trait.

        # TODO this doesnt work properly anymore because no has_unit might also
        # mean dimensionless
        # idea: attach 'needs_unit_resolution' trait to the parameter
        # once done attach `units_resolved` trait to the parameter
        """
        from faebryk.library.Expressions import is_expression
        from faebryk.library.Units import (
            UnitsNotCommensurableError,
            has_unit,
            is_unit,
            resolve_unit_expression,
        )

        params_missing_units = [
            param
            for param in root.get_children(direct_only=False, types=NumericParameter)
            if (w := param.try_get_trait(waits_for_unit)) is not None
            and not w.is_resolved()
        ]

        for param in params_missing_units:
            p_op = param.can_be_operand.get()
            constraining_operands = {
                operand
                for op in param.is_parameter_operatable.get().get_operations(
                    predicates_only=True
                )
                for operand in op.get_trait(is_expression).get_operands()
                if not (w := operand.try_get_trait(waits_for_unit)) or w.is_resolved()
            } - {p_op}

            param_unit = -1
            for operand_op in constraining_operands:
                op_obj = operand_op.get_obj_raw()
                operand_unit_node = resolve_unit_expression(
                    g=param.g, tg=param.tg, expr=op_obj.instance
                )
                operand_unit = (
                    operand_unit_node.get_is_unit() if operand_unit_node else None
                )
                if isinstance(param_unit, int) and param_unit == -1:
                    param_unit = operand_unit
                    if param_unit is not None:
                        fabll.Traits.create_and_add_instance_to(
                            node=param, trait=has_unit
                        ).setup(is_unit=param_unit)
                    param.get_trait(waits_for_unit).resolve()
                else:
                    if not is_unit.is_commensurable_with(
                        cast(None | is_unit, param_unit),
                        operand_unit,
                    ):
                        raise UnitsNotCommensurableError(
                            "Parameter constraints have incompatible units",
                            [param_unit, operand_unit],
                        )

    @staticmethod
    def validate_predicate_units_in_tree(root: fabll.Node) -> None:
        """
        Validate that all predicate expressions have commensurable operands.

        Predicates (comparisons like IsSubset, Is, GreaterThan, etc.) require their
        operands to have commensurable units. This function finds all predicates
        in the tree and validates this constraint.

        Raises UnitsNotCommensurableError if any predicate has incommensurable operands.
        """
        from faebryk.library.Expressions import is_expression, is_predicate
        from faebryk.library.Units import (
            UnitsNotCommensurableError,
            is_unit,
            resolve_unit_expression,
        )

        # Find all predicate expressions (assertions)
        predicates = [
            expr
            for expr in root.get_children(direct_only=False, types=is_expression)
            if expr.try_get_sibling_trait(is_predicate) is not None
        ]

        for predicate in predicates:
            operands = predicate.get_operands()
            if len(operands) < 2:
                continue

            # Resolve units for each operand
            operand_units: list[tuple[can_be_operand, is_unit | None]] = []
            for operand in operands:
                op_obj = operand.get_obj_raw()
                try:
                    unit_node = resolve_unit_expression(
                        g=root.g, tg=root.tg, expr=op_obj.instance
                    )
                    unit = unit_node.get_is_unit() if unit_node else None
                except Exception:
                    # If we can't resolve the unit, skip this operand
                    unit = None
                operand_units.append((operand, unit))

            # Check that all operands with units are commensurable
            first_unit: is_unit | None = None
            for operand, unit in operand_units:
                if unit is None:
                    continue
                if first_unit is None:
                    first_unit = unit
                elif not is_unit.is_commensurable_with(first_unit, unit):
                    raise UnitsNotCommensurableError(
                        "Predicate operands have incompatible units",
                        [first_unit, unit],
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
    p1.set_superset("a", "b")
    p1_po = p1.is_parameter_operatable.get()

    assert set(not_none(p1.try_extract_superset()).get_values()) == {"a", "b"}

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

    ss_lit_get = p1_po.force_extract_superset()
    assert set(fabll.Traits(ss_lit_get).get_obj(Strings).get_values()) == {"a", "b"}


def test_enum_param():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    from enum import Enum

    from faebryk.library.has_usage_example import has_usage_example
    from faebryk.library.Literals import AbstractEnums, EnumsFactory

    class _ExampleNode(fabll.Node):
        class MyEnum(Enum):
            A = "a"
            B = "b"
            C = "c"
            D = "d"

        enum_p_tg = EnumParameter.MakeChild(enum_t=MyEnum)
        constraint = AbstractEnums.MakeChild_SetSuperset(
            [enum_p_tg], MyEnum.B, MyEnum.C
        )

        _has_usage_example = has_usage_example.MakeChild(
            example="",
            language=has_usage_example.Language.ato,
        ).put_on_type()

    example_node = _ExampleNode.bind_typegraph(tg=tg).create_instance(g=g)

    # Enum Literal Type Node
    atype = EnumsFactory(_ExampleNode.MyEnum)
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
    ] == [(m.name, m.value) for m in _ExampleNode.MyEnum]

    assert AbstractEnums.get_enum_as_dict_for_type(
        node=abstract_enum_type_node, tg=tg
    ) == {m.name: m.value for m in _ExampleNode.MyEnum}

    enum_lit = enum_param.force_extract_superset()
    assert enum_lit.get_values() == ["b", "c"]

    # Enum Parameter from instance graph
    enum_p_ig = EnumParameter.bind_typegraph(tg=tg).create_instance(g=g)
    enum_p_ig.set_superset(_ExampleNode.MyEnum.B, g=g)
    assert enum_p_ig.force_extract_superset().get_values() == ["b"]


def test_string_param():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    from faebryk.library.Literals import Strings

    string_p = StringParameter.bind_typegraph(tg=tg).create_instance(g=g)
    string_p.set_superset("IG constrained")
    assert string_p.extract_singleton() == "IG constrained"

    class _ExampleStringParameter(fabll.Node):
        string_p_tg = StringParameter.MakeChild()
        constraint = Strings.MakeChild_SetSuperset([string_p_tg], "TG constrained")

    esp = _ExampleStringParameter.bind_typegraph(tg=tg).create_instance(g=g)
    assert esp.string_p_tg.get().extract_singleton() == "TG constrained"


def test_boolean_param():
    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    from faebryk.library.Literals import Booleans

    boolean_p = BooleanParameter.bind_typegraph(tg=tg).create_instance(g=g)
    boolean_p.set_singleton(value=True, g=g)
    assert boolean_p.force_extract_singleton()

    class _ExampleBooleanParameter(fabll.Node):
        boolean_p_tg = BooleanParameter.MakeChild()
        constraint = Booleans.MakeChild_SetSuperset([boolean_p_tg], True)

    ebp = _ExampleBooleanParameter.bind_typegraph(tg=tg).create_instance(g=g)
    assert ebp.boolean_p_tg.get().force_extract_singleton()


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


def test_compact_repr_param():
    """
    Test compact_repr for parameters and expressions.

    This test verifies that:
    1. Parameters use their explicit names set via set_name()
    2. Expressions are formatted with proper symbols (+, *, ≥, ¬, ∧)
    3. Units are shown in brackets for numeric parameters (e.g., A[V])
    """
    from faebryk.libs.test.boundexpressions import BoundExpressions

    E = BoundExpressions()

    # Create numeric parameters with Volt unit and explicit names
    p1_op = E.parameter_op(units=E.U.V, name="A")
    p2_op = E.parameter_op(units=E.U.V, name="B")

    # Create literals
    five_volt_op = E.lit_op_single((5.0, E.U.V))
    ten_scalar_op = E.lit_op_single(10.0)

    # Build expression: (p1 + p2 + 5V) * 10
    # (p1 + p2)
    p1_plus_p2 = E.add(p1_op, p2_op)
    # (p1 + p2 + 5V)
    sum_with_five = E.add(p1_plus_p2, five_volt_op)
    # ((p1 + p2 + 5V) * 10)
    expr = E.multiply(sum_with_five, ten_scalar_op)

    # Get expression repr
    # Parameters now show their display unit in brackets, e.g., A[V] for Volts
    expr_po = expr.as_parameter_operatable.force_get()
    exprstr = expr_po.compact_repr(no_lit_suffix=True)
    assert exprstr == "((A[V] + B[V]) + 5V) * 10"
    exprstr_w_lit_suffix = expr_po.compact_repr()
    assert exprstr_w_lit_suffix == "((A[V]⁺ + B[V]⁺) + 5V) * 10"

    # Test p2 + p1 (parameter names are stable)
    expr2 = E.add(p2_op, p1_op)
    expr2_po = expr2.as_parameter_operatable.force_get()
    expr2str = expr2_po.compact_repr(no_lit_suffix=True)
    assert expr2str == "B[V] + A[V]"
    expr2str_w_lit_suffix = expr2_po.compact_repr()
    assert expr2str_w_lit_suffix == "B[V]⁺ + A[V]⁺"

    # Create a boolean parameter with explicit name
    p3_op = E.bool_parameter_op(name="C")

    # Create Not(p3)
    expr3 = E.not_(p3_op)
    expr3_po = expr3.as_parameter_operatable.force_get()
    expr3str = expr3_po.compact_repr(no_lit_suffix=True)
    assert expr3str == "¬C"
    expr3str_w_lit_suffix = expr3_po.compact_repr()
    assert expr3str_w_lit_suffix == "¬C"

    # Create 10 V literal for comparison
    ten_volt_op = E.lit_op_single((10.0, E.U.V))

    # Create expr >= 10V
    ge_expr = E.greater_or_equal(expr, ten_volt_op)

    # Create And(Not(p3), expr >= 10V)
    expr4 = E.and_(expr3, ge_expr)
    expr4_po = expr4.as_parameter_operatable.force_get()
    expr4str = expr4_po.compact_repr(no_lit_suffix=True)
    assert expr4str == "¬C ∧ ((((A[V] + B[V]) + 5V) * 10) ≥ 10V)"
    expr4str_w_lit_suffix = expr4_po.compact_repr()
    assert expr4str_w_lit_suffix == "¬C ∧ ((((A[V]⁺ + B[V]⁺) + 5V) * 10) ≥ 10V)"

    # Test with explicitly named dimensionless parameters
    pZ_op = E.parameter_op(name="Z")
    pZ_repr = pZ_op.as_parameter_operatable.force_get().compact_repr(no_lit_suffix=True)
    assert pZ_repr == "Z"
    pZ_repr_w_lit_suffix = pZ_op.as_parameter_operatable.force_get().compact_repr()
    assert pZ_repr_w_lit_suffix == "Z⁺"

    pa_op = E.parameter_op(name="a")
    pa_repr = pa_op.as_parameter_operatable.force_get().compact_repr(no_lit_suffix=True)
    assert pa_repr == "a"
    pa_repr_w_lit_suffix = pa_op.as_parameter_operatable.force_get().compact_repr()
    assert pa_repr_w_lit_suffix == "a⁺"

    # Test Greek letters
    palpha_op = E.parameter_op(name="α")
    palpha_repr = palpha_op.as_parameter_operatable.force_get().compact_repr(
        no_lit_suffix=True
    )
    assert palpha_repr == "α"
    palpha_repr_w_lit_suffix = (
        palpha_op.as_parameter_operatable.force_get().compact_repr()
    )
    assert palpha_repr_w_lit_suffix == "α⁺"

    pbeta_op = E.parameter_op(name="β")
    pbeta_repr = pbeta_op.as_parameter_operatable.force_get().compact_repr(
        no_lit_suffix=True
    )
    assert pbeta_repr == "β"
    pbeta_repr_w_lit_suffix = (
        pbeta_op.as_parameter_operatable.force_get().compact_repr()
    )
    assert pbeta_repr_w_lit_suffix == "β⁺"

    # Test subscript names
    pAA_op = E.parameter_op(name="A₁")
    pAA_repr = pAA_op.as_parameter_operatable.force_get().compact_repr(
        no_lit_suffix=True
    )
    assert pAA_repr == "A₁"
    pAA_repr_w_lit_suffix = pAA_op.as_parameter_operatable.force_get().compact_repr()
    assert pAA_repr_w_lit_suffix == "A₁⁺"


@pytest.mark.skip(reason="xfail")  # TODO: is_congruent_to not implemented yet
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
    bool_true = (
        Booleans.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_values(True, False)
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


@pytest.mark.skip(reason="xfail")  # TODO: is_congruent_to not implemented yet
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

    assert singleton.can_be_operand.get().pretty() == "5Ω"
    assert discrete_set.can_be_operand.get().pretty() == "{1, 2, 3, 4}Ω"
    assert continuous_set.can_be_operand.get().pretty() == "{5..10}Ω"
    assert inf_set.can_be_operand.get().pretty() == "{ℝ}Ω"
    assert continuous_set_rel.can_be_operand.get().pretty() == "5±0.5%Ω"
    assert disjoint_union.can_be_operand.get().pretty() == "{5..10, 15..20}Ω"


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
    enum_param.set_superset(MyEnum.A, MyEnum.B, g=g1)

    # Verify original works
    original_lit = enum_param.force_extract_superset()
    original_values = original_lit.get_values()
    assert sorted(original_values) == ["a", "b"]

    # Get the Is expression that constrains the parameter
    original_ops = enum_param.is_parameter_operatable.get().get_operations()
    assert len(original_ops) == 1, f"Expected 1 operation, got {len(original_ops)}"
    is_expr = list(original_ops)[0]
    print(f"\nOriginal Is expression: {is_expr}")

    # Create new graph and copy the TypeGraph first
    g2 = graph.GraphView.create()
    _ = tg1.copy_into(target_graph=g2, minimal=False)

    # Copy the Is expression (not just the parameter)
    # This should copy both operands (parameter and literal) along with it
    copied_is = is_expr.copy_into(g=g2)
    print(f"Copied Is expression in g2: {copied_is}")

    # The copied parameter should now be accessible via the
    # copied Is expression's operands
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

    copied_lit = copied_param.force_extract_superset()
    copied_values = copied_lit.get_values()
    assert sorted(copied_values) == ["a", "b"], (
        f"Expected ['a', 'b'] but got {copied_values}"
    )

    # Verify we can still read the original
    assert sorted(enum_param.force_extract_superset().get_values()) == ["a", "b"]

    # Verify the enum type can still be accessed
    copied_enum_type = copied_param.get_enum_type()
    assert copied_enum_type is not None


def test_copy_numeric_parameter():
    from faebryk.library.Units import Dimensionless

    g1 = fabll.graph.GraphView.create()
    tg1 = fbrk.TypeGraph.create(g=g1)

    class _App(fabll.Node):
        numeric_param = NumericParameter.MakeChild(unit=Dimensionless)

    app = _App.bind_typegraph(tg=tg1).create_instance(g=g1)

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
    from faebryk.library.Units import Volt, decode_symbol_runtime, is_unit

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    # Create a Volt instance to register it in the typegraph
    _ = Volt.bind_typegraph(tg=tg).create_instance(g=g)

    # Get mV unit (millivolt) via decode_symbol_runtime
    mv_unit = decode_symbol_runtime(g=g, tg=tg, symbol="mV")

    # Verify mV has the correct multiplier
    assert is_unit._extract_multiplier(mv_unit) == 0.001

    # Create a numeric parameter with mV as display unit
    param = (
        NumericParameter.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup(is_unit=mv_unit)
    )

    # The has_unit trait should store the base unit (V, multiplier=1)
    base_unit = param.force_get_units()
    assert base_unit._extract_multiplier() == 1.0

    # The has_display_unit trait should store mV (multiplier=0.001)
    display_unit = param.force_get_display_units()
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
    repr_str = is_param.compact_repr(no_lit_suffix=True)

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
    param.set_superset(g=g, value=literal)

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
    base_unit = param.force_get_units()
    display_unit = param.force_get_display_units()

    assert base_unit._extract_multiplier() == 1.0
    assert display_unit._extract_multiplier() == 1.0


def test_display_unit_makechild():
    from faebryk.library.Units import Ohm, has_display_unit, has_unit

    g = fabll.graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    class _TestModule(fabll.Node):
        resistance = NumericParameter.MakeChild(unit=Ohm)

    module = _TestModule.bind_typegraph(tg=tg).create_instance(g=g)
    param = module.resistance.get()

    # Both traits should be present
    assert param.has_trait(has_unit)
    assert param.has_trait(has_display_unit)

    # Both should point to Ohm (base unit)
    base_unit = param.force_get_units()
    display_unit = param.force_get_display_units()

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
    param = (
        NumericParameter.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup(is_unit=mv_unit)
    )

    # Create a literal in base units (Volts): 5 V (singleton)
    literal = (
        Numbers.bind_typegraph(tg=tg)
        .create_instance(g=g)
        .setup_from_singleton(value=5.0, unit=volt_unit)
    )

    # Alias the parameter to the literal
    param.set_superset(g=g, value=literal)

    # Get the compact repr with lit suffix
    is_param = param.is_parameter.get()
    repr_str = is_param.compact_repr()

    # The value should be converted to display units (5V = 5000mV)
    assert "5000" in repr_str
    # Note: decode_symbol_runtime creates anonymous units without symbol preservation
    # The basis vector representation is used instead of "mV"
