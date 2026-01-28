# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Solver Invariants & Dataflow
============================

This module documents the solver's invariants and how they are maintained.

INVARIANTS
----------
The solver maintains these invariants on the expression graph:

1. **Alias Invariant** (critical):
   Every non-predicate expression must have an Is alias with exactly one parameter
   representative. Expressions cannot be direct operands; only their alias
   representatives (parameters) can be operands.

   ```
   E(A, B) -> Is!(P, E), where P is parameter representative
   operand references: P, not E
   ```

2. **No Expression Operands**:
   Expression operands in the graph must be alias representatives (parameters),
   not the expressions themselves. Algorithms must use AliasClass.of(expr).representative()
   when passing expressions as operands.

3. **No Congruence**:
   Structurally identical expressions are merged. Creating an existing expression
   returns the existing one.

4. **Pure Literal Fold**:
   Expressions with all literal operands are evaluated and bound as superset
   constraints: E(X, Y) -> E{⊆|result}(X, Y)

5. **Predicate Literal Semantics**:
   - P{⊆|True} -> P! (unasserted predicate with True subset becomes asserted)
   - P!{⊆|False} -> Contradiction

6. **Comparison Canonicalization**:
   - A >= X (X literal) -> A ⊆ [X.max(), +∞)
   - X >= A (X literal) -> A ⊆ (-∞, X.min()]
   - No A >! X or X >! A predicates remain

7. **Minimal Subsumption**:
   - A ⊆! X, A ⊆! Y -> A ⊆! (X ∩ Y)
   - X ⊆! A, Y ⊆! A -> (X ∪ Y) ⊆! A

8. **No Empty Supersets**:
   A ⊆! {} => Contradiction

9. **No Reflexive Tautologies**:
   A ⊆! A is dropped (no information)

10. **Idempotent Deduplication**:
    Or(A, A, B) -> Or(A, B)

11. **Canonical Form**:
    Expressions are created in canonical form (see convert_to_canonical_operations).


INVARIANT-BREAKING BEHAVIORS & RECOVERY
---------------------------------------
Some algorithms temporarily break invariants. Here's how they're handled:

### Expression Operands in Builders
**Problem**: Algorithms may construct ExpressionBuilder with expression operands
(e.g., upper/lower_estimation passing expr_e.as_operand.get()).

**How it breaks invariant**: Violates "No Expression Operands" - expressions
should not be direct operands.

**Recovery path** (automatic):
`_flat_expressions()` in insert_expression handles this automatically:
1. For each operand, calls `AliasClass.of(op).representative()`
2. If the operand is a non-predicate expression without a visible alias,
   creates an alias on-the-fly via `create_representative(alias=True)`
3. Returns the alias representative instead of the expression

Algorithms do NOT need explicit AliasClass handling - the invariant system
handles expression operands transparently.

### Nested Mutation During Expression Copy
**Problem**: mutate_expression calls wrap_insert_expression, which may trigger
_ss_lits_available -> get_copy -> nested mutate_expression on the same expr.

**How it breaks invariant**: Outer call tries to mutate an already-mutated expr.

**Recovery path**:
After wrap_insert_expression returns, re-check if expr was already mutated:
```python
if self.has_been_mutated(expr_po):
    return self.get_mutated(expr_po).as_operand.get()
```

### Finding Inner Expressions After Flattening
**Problem**: After alias flattening, expression operands are alias representatives
(parameters), so expr.get_operands()[0].as_expression fails.

**How it breaks invariant**: Code expects expression operands but finds parameters.

**Recovery path**:
Use AliasClass to find the aliased expression:
```python
inner_exprs = AliasClass.of(inner_expr_rep).get_with_trait(is_expression)
# Filter by type for involutory operations
expr_type = fabll.Traits(expr).get_type_node()
inner_expr = next(e for e in inner_exprs if same_type(e, expr_type))
```


DATAFLOW THROUGH wrap_insert_expression
---------------------------------------
All expression creation flows through wrap_insert_expression() which enforces
invariants in order:

1. Reflexive tautology check (drop A ⊆ A)
2. Congruence check (return existing if identical)
3. Subsumption check (merge/replace if subsumed)
4. Empty superset check (raise Contradiction)
5. Literal alias elimination (no A is! X)
6. Literal fold (compute pure literal expressions)
7. Termination marking (for completed constraints)
8. Expression creation with canonical form
9. Alias creation (for non-predicates)
10. Superset/subset constraint creation (from literal fold)

This ensures invariants are restored regardless of what the algorithm passes in.
"""

import logging
from cmath import pi
from typing import Callable, Iterable, cast

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import ExpressionBuilder, Mutator
from faebryk.core.solver.utils import S_LOG
from faebryk.libs.util import EquivalenceClasses, indented_container, not_none, one

Add = F.Expressions.Add
And = F.Expressions.And
Cardinality = F.Expressions.Cardinality
Ceil = F.Expressions.Ceil
Cos = F.Expressions.Cos
Divide = F.Expressions.Divide
Floor = F.Expressions.Floor
GreaterOrEqual = F.Expressions.GreaterOrEqual
GreaterThan = F.Expressions.GreaterThan
Implies = F.Expressions.Implies
is_predicate = F.Expressions.is_predicate
IsSubset = F.Expressions.IsSubset
IsSuperset = F.Expressions.IsSuperset
LessOrEqual = F.Expressions.LessOrEqual
LessThan = F.Expressions.LessThan
Multiply = F.Expressions.Multiply
Not = F.Expressions.Not
Or = F.Expressions.Or
Power = F.Expressions.Power
Round = F.Expressions.Round
Sin = F.Expressions.Sin
Sqrt = F.Expressions.Sqrt
Subtract = F.Expressions.Subtract
Xor = F.Expressions.Xor

logger = logging.getLogger(__name__)
if S_LOG:
    logger.setLevel(logging.DEBUG)


def _strip_units(
    mutator: Mutator,
    operand: F.Parameters.can_be_operand,
) -> F.Parameters.can_be_operand:
    if np := fabll.Traits(operand).get_obj_raw().try_cast(F.Literals.Numbers):
        return (
            np.convert_to_dimensionless(g=mutator.G_transient, tg=mutator.tg_out)
            .is_literal.get()
            .as_operand.get()
        )
    if (
        numparam := fabll.Traits(operand)
        .get_obj_raw()
        .try_cast(F.Parameters.NumericParameter)
    ):
        if unit := numparam.try_get_units():
            assert unit._extract_multiplier() == 1.0, (
                "Parameter units must not use scalar multiplier"
            )
            assert unit._extract_offset() == 0.0, "Parameter units must not use offset"

    return operand


@algorithm("Canonicalize", single=True, terminal=False)
def convert_to_canonical_operations(mutator: Mutator):
    """

    Canonicalize expression types:
    Transforms Sub-Add to Add-Add
    ```
    A - B -> A + (-1 * B)
    A / B -> A * B^-1
    A <= B -> B >= A
    A < B -> B > A
    A superset B -> B subset A
    Logic (xor, and, implies) -> Or & Not
    floor/ceil -> round(x -/+ 0.5)
    cos(x) -> sin(x + pi/2)
    sqrt(x) -> x^-0.5
    min(x) -> p, p ss x, p le x
    max(x) -> p, p ss x, p ge x
    ```

    Canonicalize literals in expressions and parameters:
    - remove units for Numbers
    - bool -> BoolSet
    - Enum -> P_Set[Enum]
    - remove unit expressions
    """

    UnsupportedOperations: dict[type[fabll.NodeT], type[fabll.NodeT] | None] = {
        GreaterThan: GreaterOrEqual,
        LessThan: LessOrEqual,
        Cardinality: None,
    }
    _UnsupportedOperations = {
        fabll.TypeNodeBoundTG.get_or_create_type_in_tg(mutator.tg_in, k)
        .node()
        .get_uuid(): v
        for k, v in UnsupportedOperations.items()
    }

    def c(
        op: type[fabll.NodeT], *operands: F.Parameters.can_be_operand
    ) -> F.Parameters.can_be_operand | None:
        out = mutator.create_check_and_insert_expression(
            cast(type[F.Expressions.ExpressionNodes], op),
            *operands,
            from_ops=getattr(c, "from_ops", None),
        ).out
        if out is None:
            return None
        return out.as_operand.get()

    def curry(e_type: type[fabll.NodeT]):
        def _(*operands: F.Parameters.can_be_operand | F.Literals.LiteralValues | None):
            _operands = [
                mutator.make_singleton(o).can_be_operand.get()
                if not isinstance(o, fabll.Node)
                else o
                for o in operands
                if o is not None
            ]
            return c(e_type, *_operands)

        return _

    # CanonicalNumeric
    Add_ = curry(Add)
    Multiply_ = curry(Multiply)
    Power_ = curry(Power)
    # Round_ = curry(Round)
    # Abs_ = curry(Abs)
    # Sin_ = curry(Sin)
    # Log_ = curry(Log)

    # CanonicalLogic
    Or_ = curry(Or)
    Not_ = curry(Not)

    # CanonicalPredicate
    # GreaterOrEqual_ = curry(GreaterOrEqual)
    # IsSubset_ = curry(IsSubset)
    # Is_ = curry(Is)
    # GreaterThan_ = curry(GreaterThan)

    MirroredExpressions: list[
        tuple[
            type[fabll.NodeT],
            type[fabll.NodeT],
            Callable[
                [list[F.Parameters.can_be_operand]],
                list[F.Parameters.can_be_operand | None],
            ],
        ]
    ] = [
        (
            Add,
            Subtract,
            lambda operands: [operands[0], *(Multiply_(o, -1) for o in operands[1:])],
        ),
        (
            Multiply,
            Divide,
            lambda operands: [operands[0], *(Power_(o, -1) for o in operands[1:])],
        ),
        (
            Not,
            And,
            lambda operands: [Or_(*[Not_(o) for o in operands])],
        ),
        (
            Or,
            Implies,
            lambda operands: [Not_(operands[0]), *operands[1:]],
        ),
        (
            Not,
            Xor,
            lambda operands: [
                Or_(Not_(Or_(*operands)), Not_(Or_(*[Not_(o) for o in operands])))
            ],
        ),
        (
            Round,
            Floor,
            lambda operands: [Add_(*operands, -0.5)],
        ),
        (
            Round,
            Ceil,
            lambda operands: [Add_(*operands, 0.5)],
        ),
        (
            Sin,
            Cos,
            lambda operands: [Add_(*operands, pi / 2)],
        ),
        (
            Power,
            Sqrt,
            lambda operands: [
                *operands,
                mutator.make_singleton(0.5).can_be_operand.get(),
            ],
        ),
        (
            GreaterOrEqual,
            LessOrEqual,
            lambda operands: list(reversed(operands)),
        ),
        (
            # GreaterThan,
            # TODO
            GreaterOrEqual,
            LessThan,
            lambda operands: list(reversed(operands)),
        ),
        # TODO remove once support for LT/GT
        (
            GreaterOrEqual,
            GreaterThan,
            lambda operands: list(operands),
        ),
        (
            IsSubset,
            IsSuperset,
            lambda operands: list(reversed(operands)),
        ),
    ]

    lookup = {
        Convertible.bind_typegraph(mutator.tg_in)
        .get_or_create_type()
        .node()
        .get_uuid(): (
            Target,
            Converter,
        )
        for Target, Convertible, Converter in MirroredExpressions
    }

    exprs = mutator.get_expressions()

    for e in exprs:
        e_type = not_none(fabll.Traits(e).get_obj_raw().get_type_node()).node()
        e_type_uuid = e_type.get_uuid()
        e_po = e.as_parameter_operatable.get()

        if e_type_uuid in _UnsupportedOperations:
            replacement = _UnsupportedOperations[e_type_uuid]
            rep = e.compact_repr()
            if replacement is None:
                logger.warning(f"{type(e)}({rep}) not supported by solver, skipping")
                mutator.remove(e.as_parameter_operatable.get())
                continue

            logger.warning(
                f"{type(e)}({rep}) not supported by solver, converting to {replacement}"
            )

        operands = e.get_operands()
        from_ops = [e_po]

        # Canonical-expressions need to be mutated to strip the units
        if e_type_uuid not in lookup:
            mutator.mutate_expression(e, operands)
            continue

        # Rest
        Target, Converter = lookup[e_type_uuid]

        setattr(c, "from_ops", from_ops)
        converted = [op for op in Converter(operands) if op]
        mutator.mutate_expression(
            e,
            converted,
            expression_factory=Target,  # pyright: ignore[reportArgumentType]
        )


def _remove_unit_expressions(
    mutator: Mutator, exprs: Iterable[F.Expressions.is_expression]
) -> list[F.Expressions.is_expression]:
    # Filter expressions that compute ON unit types themselves (e.g. Second^1, Ampere*Second). #noqa: E501
    # These have is_unit trait as operands (the unit type IS the operand).
    # NOT expressions like `A is {0.1..0.6}As` where operands HAVE units - those
    # should pass through and have their units stripped by _strip_units().
    unit_computation_leaves = {
        e for e in exprs if e.get_operands_with_trait(F.Units.is_unit)
    }
    unit_exprs_all = {
        parent.get_trait(F.Expressions.is_expression)
        for e in unit_computation_leaves
        for parent in e.as_operand.get().get_operations(recursive=True)
    } | unit_computation_leaves
    exprs = [e for e in exprs if e not in unit_exprs_all]
    for u_expr in unit_exprs_all:
        mutator.remove(u_expr.as_parameter_operatable.get(), no_check_roots=True)

    # Also remove UnitExpression nodes (like As = Ampere*Second).
    # These have is_parameter_operatable trait but aren't expressions or parameters,
    # so they would cause errors during copy_operand.
    for unit_expr in fabll.Traits.get_implementors(
        F.Units.is_unit_expression.bind_typegraph(mutator.tg_in), mutator.G_in
    ):
        mutator.remove(
            unit_expr.get_sibling_trait(F.Parameters.is_parameter_operatable),
            no_check_roots=True,
        )
    return exprs


@algorithm("Flatten expressions", single=True, terminal=False)
def flatten_expressions(mutator: Mutator):
    """
    Flatten nested expressions: f(g(A)) -> f(B), B is! g(A)
    """
    # TODO: consider shortcut for pure literal expressions

    # Don't use standard mutation interfaces here because they will trigger invariant checks

    # Strategy
    # - strip unit expressions
    # - go from leaf expressionsto root
    # - operand map
    #  - strip unit from lits
    #  - map exprs to repr
    #  - copy param (strip unit etc)
    # - copy expr
    # - create representative for expr
    #  - if aliases before use
    #  - else new

    # How we deal with alias classes
    # - every expr has an alias class with exactly 1 parameter and at least 1 expr (itself)
    #  - except predicates, those have no aliases
    # - expressions only have literals or parameters as operands, except "Is"
    # - if we create new expressions we need to make sure it has the representative
    #  - congruent/subsumed/dropped, nothing to do
    #  - copy/adjust, create new repr since no alias yet
    # - if we mutate expr
    #  - if congruent, merge old alias class into congruent expr
    #  - if subsumed/subsuming, no alias for predicates
    #  - if copy/adjusted, copy alias over

    # We never auto-copy an Is!, its never nested, so not triggered outside of copy_unmutated
    # - all is! have to be manually copied
    # Attention: Changed this. Is! just go through the same invariant mechanism now

    exprs = F.Expressions.is_expression.sort_by_depth_expr(mutator.get_expressions())

    exprs = _remove_unit_expressions(mutator, exprs)

    expr_reprs: dict[F.Expressions.is_expression, F.Parameters.can_be_operand] = {}
    class_reprs: dict[
        frozenset[F.Parameters.is_parameter_operatable], F.Parameters.can_be_operand
    ] = {}

    # build eq classes
    expr_pos = [e.as_parameter_operatable.get() for e in exprs]
    classes = EquivalenceClasses(expr_pos)
    for e in exprs:
        e_obj = fabll.Traits(e).get_obj_raw()
        if e_obj.isinstance(F.Expressions.Is) and e_obj.has_trait(
            F.Expressions.is_predicate
        ):
            ops = e.get_operand_operatables()
            classes.add_eq(*ops)

    alias_classes = [frozenset(class_) for class_ in classes.get()]

    # build representative for each class
    for class_ in alias_classes:
        class_params = {p for elem in class_ if (p := elem.as_parameter.try_get())}
        class_exprs = {e for elem in class_ if (e := elem.as_expression.try_get())}

        # no need to create representative for predicates
        # if param exists, need to keep it to alias it to True
        has_predicate = any(
            e.try_get_sibling_trait(F.Expressions.is_predicate) for e in class_exprs
        )
        if has_predicate:
            for e in class_exprs:
                expr_reprs[e] = mutator.make_singleton(True).can_be_operand.get()
        if not class_params and has_predicate:
            continue

        if class_params:
            p_old = next(iter(class_params))
            p = mutator.mutate_parameter(p_old)
            if S_LOG:
                exprs_repr = indented_container(
                    [e.compact_repr() for e in class_exprs], use_repr=False
                )
                logger.debug(
                    f"Using and mutating {p_old.compact_repr(no_lit_suffix=True)} -> {p.compact_repr()} "
                    f"for {indented_container([c.compact_repr() for c in class_], use_repr=False)}"
                )
        else:
            p = (
                next(iter(class_))
                .as_expression.force_get()
                .create_representative(g=mutator.G_out, tg=mutator.tg_out, alias=False)
            )
            if S_LOG:
                exprs_repr = indented_container(
                    [e.compact_repr() for e in class_exprs], use_repr=False
                )
                logger.debug(f"Using created {p.compact_repr()} for {exprs_repr}")
            mutator.register_created_parameter(p, from_ops=[])

        class_reprs[class_] = p.as_operand.get()
        p_po = p.as_parameter_operatable.get()

        if has_predicate:
            mutator._create_and_insert_expression(
                ExpressionBuilder(
                    F.Expressions.IsSubset,
                    [
                        p.as_operand.get(),
                        mutator.make_singleton(True).can_be_operand.get(),
                    ],
                    assert_=True,
                    terminate=True,
                    traits=[],
                )
            )
            continue

        # replace exprs as operands with representative (comes further down)
        if not has_predicate:
            for e in class_exprs:
                expr_reprs[e] = p.as_operand.get()
        # map all params to representative
        for p in class_params:
            mutator._mutate(p.as_parameter_operatable.get(), p_po)

    def _map_operand(
        mutator: Mutator, o: F.Parameters.can_be_operand
    ) -> F.Parameters.can_be_operand:
        o = _strip_units(mutator, o)
        if o_e := o.try_get_sibling_trait(F.Expressions.is_expression):
            o = expr_reprs[o_e]
        elif (
            o_p := o.try_get_sibling_trait(F.Parameters.is_parameter)
        ) and mutator.has_been_mutated(o_p.as_parameter_operatable.get()):
            return mutator.get_mutated(
                o_p.as_parameter_operatable.get()
            ).as_operand.get()
        return mutator.get_copy(o)

    # copy/flatten exprs
    for e in exprs:
        # aliases are manually created
        if (
            fabll.Traits(e).get_obj_raw().isinstance(F.Expressions.Is)
            and e.try_get_sibling_trait(F.Expressions.is_predicate)
            and not e.get_operand_literals()
        ):
            continue

        e_po = e.as_parameter_operatable.get()

        # parents = e_op.get_operations() - aliases
        original_operands = e.get_operands()
        operands = [_map_operand(mutator, o) for o in original_operands]
        copy_only = all(
            o1.is_same(o2, allow_different_graph=True)
            for o1, o2 in zip(original_operands, operands)
        )

        mutator._mutate(
            e_po,
            mutator._create_and_insert_expression(
                ExpressionBuilder.from_e(e).with_(operands=operands)
            ).is_parameter_operatable.get(),
        )

        if copy_only:
            mutator.transformations.copied.add(e_po)

    # TODO careful with predicates
    # build alias classes in new graph
    for class_ in alias_classes:
        class_exprs = {e for c in class_ if (e := c.as_expression.try_get())}

        # if any expr is predicate, dont create alias, and mark others all predicates
        if any(
            e.try_get_sibling_trait(F.Expressions.is_predicate) for e in class_exprs
        ):
            for e in class_exprs:
                if not e.try_get_sibling_trait(F.Expressions.is_predicate):
                    fabll.Traits.create_and_add_instance_to(
                        fabll.Traits(e).get_obj_raw(), F.Expressions.is_predicate
                    )
            continue

        class_param_op = class_reprs[class_]

        if not class_exprs:
            # no point in creating alias for just the parameter
            # all the othe param alias get dropped
            continue

        # build big alias with all exprs and the representative
        alias = mutator._create_and_insert_expression(
            ExpressionBuilder(
                F.Expressions.Is,
                [
                    mutator.get_mutated(
                        e.as_parameter_operatable.get()
                    ).as_operand.get()
                    for e in class_exprs
                ]
                + [class_param_op],
                assert_=True,
                terminate=True,
                traits=[],
            )
        )
        alias_po = alias.is_parameter_operatable.get()

        # mutate old aliases
        for c in class_:
            for is_ in c.get_operations(F.Expressions.Is, predicates_only=True):
                mutator._mutate(
                    is_.is_parameter_operatable.get(),
                    alias_po,
                )
