# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import math
from itertools import combinations

import faebryk.core.node as fabll
import faebryk.library._F as F
import faebryk.library.Expressions as Expressions
from faebryk.core.solver.algorithm import algorithm
from faebryk.core.solver.mutator import Mutator
from faebryk.core.solver.utils import Contradiction, ContradictionByLiteral
from faebryk.libs.util import (
    EquivalenceClasses,
    groupby,
)

logger = logging.getLogger(__name__)

Add = F.Expressions.Add
GreaterOrEqual = F.Expressions.GreaterOrEqual
Is = F.Expressions.Is
IsSubset = F.Expressions.IsSubset
Multiply = F.Expressions.Multiply
Power = F.Expressions.Power

# TODO: mark terminal=False where applicable


@algorithm("Check literal contradiction", terminal=False)
def check_literal_contradiction(mutator: Mutator):
    """
    Check if a literal is contradictory
    """

    mutator.get_literal_mappings(new_only=False, allow_subset=True)


@algorithm("Convert inequality with literal to subset", terminal=False)
def convert_inequality_with_literal_to_subset(mutator: Mutator):
    # TODO if not! A <= x it can be replaced by A intersect [-inf, a] is {}
    """
    This only works for inequalities we know cannot evaluate to {True, False}
    A >=! 5 -> A ss! [5, inf)
    5 >=! A -> A ss! (-inf, 5]

    A >=! [1, 10] -> A ss! [10, inf)
    [1, 10] >=! A -> A ss! (-inf, 1]
    """

    ge_exprs = {
        e
        for e in mutator.get_typed_expressions(GreaterOrEqual, sort_by_depth=True)
        # Look for expressions with only one non-literal operand
        if e.try_get_trait(F.Expressions.is_predicate)
        and len(
            [
                op
                for op in e.get_trait(F.Expressions.is_expression).get_operands()
                if op.is_parameter_operatable()
            ]
        )
        == 1
    }

    for ge in ge_exprs:
        ge_e = ge.get_trait(F.Expressions.is_expression)
        op_0 = ge_e.get_operands()[0]
        op_1 = ge_e.get_operands()[1]
        is_left = op_0.try_get_sibling_trait(F.Parameters.is_parameter_operatable)

        if is_left:
            param = op_0
            lit = op_1.get_sibling_trait(F.Literals.is_literal)
            lit_n = fabll.Traits(lit).get_obj(F.Literals.Numbers)
            boundary = lit_n.max_elem()
            if boundary.op_greater_or_equal(mutator.make_lit(math.inf)):
                if ge.try_get_trait(F.Expressions.is_predicate):
                    raise Contradiction(
                        "GreaterEqual inf not possible",
                        involved=[param.as_parameter_operatable()],
                        mutator=mutator,
                    )
                mutator.utils.alias_is_literal_and_check_predicate_eval(
                    ge_e, mutator.make_lit(False)
                )
                continue
            interval = boundary
        else:
            param = op_1
            lit = op_0.get_sibling_trait(F.Literals.is_literal)
            lit_n = fabll.Traits(lit).get_obj(F.Literals.Numbers)
            boundary = lit_n.min_elem()
            if boundary.op_greater_or_equal(mutator.make_lit(math.inf)):
                if ge.try_get_trait(F.Expressions.is_predicate):
                    raise Contradiction(
                        "LessEqual -inf not possible",
                        involved=[param.as_parameter_operatable()],
                        mutator=mutator,
                    )
                mutator.utils.alias_is_literal_and_check_predicate_eval(
                    ge_e, mutator.make_lit(False)
                )
                continue
            interval = boundary

        mutator.mutate_expression(
            ge_e,
            operands=[param, interval.get_trait(F.Parameters.can_be_operand)],
            expression_factory=IsSubset,
        )


@algorithm("Remove unconstrained", terminal=True)
def remove_unconstrained(mutator: Mutator):
    """
    Remove all expressions that are not involved in any predicates
    or expressions with side effects
    Note: Not possible for Parameters, want to keep those around for REPR
    """
    objs = mutator.get_typed_expressions()
    for obj in objs:
        obj_po = obj.get_trait(F.Parameters.is_parameter_operatable)
        if obj.try_get_trait(F.Expressions.is_predicate):
            continue
        if obj.has_trait(Expressions.has_side_effects):
            continue
        if any(
            e.try_get_trait(F.Expressions.is_predicate)
            or e.has_trait(Expressions.has_side_effects)
            for e in mutator.utils.get_expressions_involved_in(obj_po)
        ):
            continue
        mutator.remove(obj_po)


@algorithm("Remove congruent expressions", terminal=False)
def remove_congruent_expressions(mutator: Mutator):
    """
    Remove expressions that are congruent to other expressions

    ```
    X1 := A + B, X2 := A + B -> [{X1, X2}, {A}, {B}]
    ```
    """
    # X1 = A + B, X2 = A + B -> X1 is X2
    # No (Invalid): X1 = A + [0, 10], X2 = A + [0, 10]
    # No (Automatic): X1 = A + C, X2 = A + B, C ~ B -> X1 ~ X2

    all_exprs = mutator.get_expressions(sort_by_depth=True)
    # optimization: can't be congruent if they have uncorrelated literals
    all_exprs = [e for e in all_exprs if not e.get_uncorrelatable_literals()]
    # TODO is this fully correct?
    # optimization: Is, IsSubset already handled
    all_exprs = [
        e
        for e in all_exprs
        if not (
            e.expr_isinstance(F.Expressions.Is, F.Expressions.IsSubset)
            and e.try_get_sibling_trait(F.Expressions.is_predicate)
            and e.get_operand_literals()
        )
    ]
    exprs_by_type = groupby(
        all_exprs,
        lambda e: (
            type(e),
            len(e.get_operands()),
            None
            if not e.try_get_trait(F.Expressions.is_assertable)
            else e.try_get_trait(F.Expressions.is_predicate),
        ),
    )
    full_eq = EquivalenceClasses[fabll.NodeT](all_exprs)

    for exprs in exprs_by_type.values():
        if len(exprs) <= 1:
            continue
        # TODO use hash to speed up comparisons
        for e1, e2 in combinations(exprs, 2):
            # no need for recursive, since subexpr already merged if congruent
            if not full_eq.is_eq(e1, e2) and e1.is_congruent_to(e2, recursive=False):
                full_eq.add_eq(e1, e2)

    repres = {}
    for expr in all_exprs:
        eq_class = full_eq.classes[expr]
        if len(eq_class) <= 1:
            continue

        return
        eq_id = id(eq_class)
        if eq_id not in repres:
            representative = mutator.mutate_expression(expr)
            repres[eq_id] = representative

            # propagate constrained & terminate
            if Expressions.is_assertable_node(representative):
                representative.constrained = any(e.constrained for e in eq_class)
                if any(mutator.is_predicate_terminated(e) for e in eq_class):
                    mutator.predicate_terminate(representative, new_graph=True)

        mutator._mutate(expr, repres[eq_id])


@algorithm("Alias classes", terminal=False)
def resolve_alias_classes(mutator: Mutator):
    """
    Resolve alias classes
    Ignores literals
    ```
    A alias B
    B alias C
    C alias D + E
    D + E < 5
    D + E is 3
    D + E + F < 10
    -> A,B,C => R, R alias D + E, R < 5, R is 3, R + F < 10

    # Notes:
    D is 2, E is 5 -> D + E is 7, D + E is R, R is 3
    (D + E) - (D + E) -> R - R
    (D + E) + E -> R + E

    Careful: Aliases to literals will not be resolved due to loss
    of correlation information
    ```
    """

    # A is B, B is C, D is E, F, G is (A+B)
    # -> [{A, B, C}, {D, E}, {F}, {G, (A+B)}]
    param_ops = mutator.get_parameter_operatables()
    full_eq = EquivalenceClasses[F.Parameters.is_parameter_operatable](param_ops)
    is_exprs = mutator.utils.get_all_aliases()
    for is_expr in is_exprs:
        ops: set[F.Parameters.is_parameter_operatable] = {
            # Literal expressions are basically literals
            o
            for o in is_expr.get_trait(
                F.Expressions.is_expression
            ).get_operand_operatables()
            if not mutator.utils.is_literal_expression(o.as_operand())
        }
        # eq between non-literal operands
        full_eq.add_eq(*ops)
    p_eq_classes = full_eq.get(only_multi=True)

    # Make new param repre for alias classes
    for eq_class in p_eq_classes:
        eq_class_params = [
            p_po
            for p in eq_class
            if (p_po := p.try_get_sibling_trait(F.Parameters.is_parameter))
        ]
        eq_class_exprs = {
            p_e
            for p in eq_class
            if (p_e := p.try_get_sibling_trait(F.Expressions.is_expression))
        }

        if not eq_class_params:
            continue

        if len(eq_class_params) == 1:
            print(
                "Single param", eq_class_params[0].compact_repr(mutator.print_context)
            )
            # check if all in eq_class already aliased
            # Then no need to to create new representative
            _repr = eq_class_params[0]
            _repr_po = _repr.as_parameter_operatable()
            iss = _repr_po.get_operations(F.Expressions.Is)
            iss_exprs = {
                o
                for e in iss
                for o in e.get_trait(
                    F.Expressions.is_expression
                ).get_operands_with_trait(F.Expressions.is_expression)
            }
            if eq_class_exprs.issubset(iss_exprs):
                # check if all predicates are already propagated
                class_expressions = {
                    e
                    for operand in eq_class_exprs
                    for e in operand.as_parameter_operatable().get_operations()
                    # skip POps Is, because they create the alias classes
                    # or literal aliases (done by distribute algo)
                    if not (
                        (
                            e_expr := e.get_trait(F.Expressions.is_expression)
                        ).expr_isinstance(F.Expressions.Is)
                        and e.try_get_trait(F.Expressions.is_predicate)
                    )
                    # skip literal subsets (done by distribute algo)
                    and not (
                        e_expr.expr_isinstance(F.Expressions.IsSubset)
                        and e_expr.get_operand_literals()
                        and e.try_get_trait(F.Expressions.is_predicate)
                    )
                }
                if not class_expressions:
                    continue
            # else
            mutator.get_copy_po(_repr_po)
            continue

        # Merge param alias classes
        representative = mutator.utils.merge_parameters(eq_class_params)

        for p in eq_class_params:
            mutator._mutate(
                p.as_parameter_operatable(), representative.as_parameter_operatable()
            )

    for eq_class in p_eq_classes:
        eq_class_params = [
            p
            for p in eq_class
            if (p_po := p.try_get_sibling_trait(F.Parameters.is_parameter))
        ]
        eq_class_exprs = {
            p_e
            for p in eq_class
            if (p_e := p.try_get_sibling_trait(F.Expressions.is_expression))
        }

        if eq_class_params:
            p_0 = eq_class_params[0]
            # See len(alias_class_params) == 1 case above
            if not mutator.has_been_mutated(p_0):
                continue
            representative = mutator.get_mutated(p_0)
        else:
            # If not params or lits in class, create a new param as representative
            # for expressions

            # single domain
            # TODO need to ask expression output for type
            # .... thats annoying though
            representative = mutator.register_created_parameter(
                F.Parameters.BooleanParameter.bind_typegraph(mutator.tg_out)
                .create_instance(g=mutator.G_out)
                .get_trait(F.Parameters.is_parameter),
                from_ops=list(eq_class),
            ).as_parameter_operatable()

        for e in eq_class_exprs:
            e_po = e.as_parameter_operatable()
            mutator.soft_replace(e_po, representative)
            if mutator.utils.are_aliased(e_po, *eq_class_params):
                continue
            mutator.utils.alias_to(
                e.as_operand(), representative.as_operand(), from_ops=list(eq_class)
            )


@algorithm("Merge intersecting subsets", terminal=False)
def merge_intersect_subsets(mutator: Mutator):
    """
    A subset L1
    A subset L2
    -> A subset (L1 & L2)

    x = A subset L1
    y = A subset L2
    Z = x and y -> Z = x & y
    -> A subset (L1 & L2)
    """

    # TODO use Intersection/Union expr
    # A ss B, A ss C -> A ss (B & C)
    # and then use literal folding
    # should also work for others:
    #   A < B, A < C -> A < (B | C)
    # Got to consider when to Intersect/Union is more useful than the associative

    # this merge is already done implicitly by try_extract_literal
    # but it's still needed to create the explicit subset op

    params = mutator.get_parameter_operatables(sort_by_depth=True)

    for param in params:
        ss_lits = {
            lit: vs
            for k, vs in mutator.utils.get_supersets(param).items()
            if (lit := mutator.utils.is_literal(k))
        }
        if len(ss_lits) <= 1:
            continue

        intersected = F.Literals.is_literal.intersect_all(*ss_lits.keys())

        # short-cut, would be detected by subset_to
        if intersected.is_empty():
            raise ContradictionByLiteral(
                "Intersection of literals is empty",
                involved=[param],
                literals=list(ss_lits.keys()),
                mutator=mutator,
            )

        old_sss = [old_ss for old_sss in ss_lits.values() for old_ss in old_sss]

        # already exists
        if intersected in ss_lits:
            target = ss_lits[intersected][0]
        else:
            target = mutator.utils.subset_to(
                param.as_operand(),
                intersected.as_operand(),
                from_ops=[
                    old_ss.get_trait(F.Parameters.is_parameter_operatable)
                    for old_ss in old_sss
                ],
            )
            target_obj = fabll.Traits(target).get_obj_raw()
            assert target_obj.isinstance(F.Expressions.IsSubset, F.Expressions.Is)

        # Merge
        for old_ss in old_sss:
            old_ss_po = old_ss.get_trait(F.Parameters.is_parameter_operatable)
            target_po = target.get_sibling_trait(F.Parameters.is_parameter_operatable)
            mutator._mutate(
                old_ss_po,
                mutator.get_copy_po(target_po),
            )


@algorithm("Empty set", terminal=False)
def empty_set(mutator: Mutator):
    """
    A is {} -> False
    A ss {} -> False
    """

    # A is {} -> False
    for e in mutator.get_typed_expressions(Is):
        e_expr = e.get_trait(F.Expressions.is_expression)
        lits = e_expr.get_operand_literals()
        if not lits:
            continue
        if any(lit.is_empty() for lit in lits.values()):
            mutator.utils.alias_is_literal_and_check_predicate_eval(
                e_expr, mutator.make_lit(False)
            )

    # A ss {} -> False
    # Converted by literal_folding


@algorithm("Transitive subset", terminal=False)
def transitive_subset(mutator: Mutator):
    """
    ```
    A ss! B, B ss! C -> new A ss! C
    A ss! B, B is! X -> new A ss! X
    ```
    """
    # for all A ss! B | B not lit
    for ss_op in mutator.utils.get_all_subsets():
        ss_op_e = ss_op.get_trait(F.Expressions.is_expression)
        ss_op_po = ss_op.get_trait(F.Parameters.is_parameter_operatable)
        A, B = ss_op_e.get_operands()
        if not (B_po := B.try_get_sibling_trait(F.Parameters.is_parameter_operatable)):
            continue

        # all B ss! C | C not A
        for C, es in mutator.utils.get_supersets(B_po).items():
            if C is A:
                continue
            # create A ss! C/X
            mutator.utils.subset_to(
                A,
                C,
                from_ops=[
                    ss_op_po,
                    *(e.get_trait(F.Parameters.is_parameter_operatable) for e in es),
                ],
            )

        # all B is! X, X lit
        # for non-lits done by eq classes
        X = mutator.utils.try_extract_literal(B_po)
        if X is not None:
            mutator.utils.subset_to(A, X.as_operand(), from_ops=[ss_op_po, B_po])


@algorithm("Predicate flat terminate", terminal=False)
def predicate_flat_terminate(mutator: Mutator):
    """
    ```
    P!(A, Lit) -> P!!(A, Lit)
    P!(Lit1, Lit2) -> P!!(Lit1, Lit2)
    ```

    Terminates all (dis)proven predicates that contain no expressions.
    """
    predicates = mutator.get_expressions(required_traits=(F.Expressions.is_predicate,))
    for p_e in predicates:
        p_po = p_e.as_parameter_operatable()
        if any(p_e.get_operands_with_trait(F.Expressions.is_expression)):
            continue

        # only (dis)proven
        if mutator.utils.try_extract_literal(p_po) is None:
            continue

        mutator.predicate_terminate(p_e.get_sibling_trait(F.Expressions.is_predicate))


@algorithm("Predicate is!! True", terminal=False)
def predicate_terminated_is_true(mutator: Mutator):
    """
    P!! is! True -> P!! is!! True
    """

    for p in mutator.get_typed_expressions(Is):
        if not (p_c := p.try_get_trait(F.Expressions.is_predicate)):
            continue
        if mutator.is_predicate_terminated(p_c):
            continue
        p_e = p.get_trait(F.Expressions.is_expression)
        if not any(
            lit.equals_singleton(True) for lit in p_e.get_operand_literals().values()
        ):
            continue
        if not (op_operatables := p_e.get_operand_operatables()):
            continue
        op = next(iter(op_operatables))
        if not (
            op_c := op.try_get_trait(F.Expressions.is_predicate)
        ) or not mutator.is_predicate_terminated(op_c):
            continue

        mutator.predicate_terminate(p_c)


@algorithm("Convert aliased singletons into literals", terminal=False)
def convert_operable_aliased_to_single_into_literal(mutator: Mutator):
    """
    A is ([5]), A + B -> ([5]) + B
    A is [True], A ^ B -> [True] ^ B
    """

    exprs = mutator.get_expressions(sort_by_depth=True)
    for e in exprs:
        if mutator.utils.is_pure_literal_expression(e.as_operand()):
            continue
        e_po = e.as_parameter_operatable()
        # handled in _todo
        if mutator.utils.is_alias_is_literal(e_po) or mutator.utils.is_subset_literal(
            e_po
        ):
            continue
        # not handling here
        if (
            e.expr_isinstance(F.Expressions.Is, F.Expressions.IsSubset)
            and e.try_get_trait(F.Expressions.is_predicate)
            and any(e.get_operands_with_trait(F.Expressions.is_predicate))
        ):
            continue

        ops = []
        found_literal = False
        for op in e.get_operands():
            lit = mutator.utils.is_replacable_by_literal(op)
            # preserve non-replaceable operands
            # A + B + C | A is ([5]) -> B, C
            if lit is None:
                ops.append(op)
                continue
            ops.append(lit)
            found_literal = True

        if not found_literal:
            continue

        mutator.mutate_expression(e, operands=ops)


@algorithm("Isolate lone parameters", terminal=False)
def isolate_lone_params(mutator: Mutator):
    """
    If an expression is aliased to a literal, and only one parameter in the expression
    is not aliased to a literal, isolate the lone parameter on one side of the
    expression.

    Inversion operations must be constructed using canonical operators only.

    A + B is Lit1, B is Lit2, A further uncorrelated B -> A is Lit1 + (Lit2 * -1)
    """

    def _isolate_param(
        param: F.Parameters.is_parameter_operatable,
        op_with_param: F.Parameters.is_parameter_operatable,
        op_without_param: F.Parameters.can_be_operand,
        from_expr: F.Expressions.is_expression,
    ) -> tuple[F.Parameters.can_be_operand, F.Parameters.can_be_operand]:
        if not (op_with_param_e := op_with_param.is_expresssion()):
            return op_with_param.as_operand(), op_without_param

        def op_or_create_expr(
            operation: type[fabll.NodeT], *operands: F.Parameters.can_be_operand
        ) -> F.Parameters.can_be_operand:
            if len(operands) == 1:
                return operands[0]

            return mutator.create_expression(
                operation,
                *operands,
                from_ops=[from_expr.get_trait(F.Parameters.is_parameter_operatable)],
            ).as_operand()

        retained_ops = [
            op
            for op in op_with_param_e.get_operands()
            if param in mutator.utils.find_unique_params(op)
        ]

        moved_ops = [
            op
            for op in op_with_param_e.get_operands()
            if param not in mutator.utils.find_unique_params(op)
        ]

        if not moved_ops:
            return op_with_param.as_operand(), op_without_param

        op_node = fabll.Traits(op_with_param).get_obj_raw()
        if op_node.isinstance(F.Expressions.Add):
            return (
                op_or_create_expr(Add, *retained_ops),
                op_or_create_expr(
                    Add,
                    op_without_param,
                    *[
                        op_or_create_expr(
                            Multiply,
                            op,
                            mutator.make_lit(-1).get_trait(F.Parameters.can_be_operand),
                        )
                        for op in moved_ops
                    ],
                ),
            )
        elif op_node.isinstance(F.Expressions.Multiply):
            return (
                op_or_create_expr(Multiply, *retained_ops),
                op_or_create_expr(
                    Multiply,
                    op_without_param,
                    op_or_create_expr(
                        Power,
                        op_or_create_expr(Multiply, *moved_ops),
                        mutator.make_lit(-1).get_trait(F.Parameters.can_be_operand),
                    ),
                ),
            )
        elif op_node.isinstance(F.Expressions.Power):
            return (
                op_with_param_e.get_operands()[0],
                op_or_create_expr(
                    Power,
                    op_without_param,
                    mutator.make_lit(-1).get_trait(F.Parameters.can_be_operand),
                ),  # TODO: fix exponent
            )
        else:
            return op_with_param.as_operand(), op_without_param

    def isolate_param(
        expr: F.Expressions.is_expression, param: F.Parameters.is_parameter_operatable
    ) -> (tuple[F.Parameters.can_be_operand, F.Parameters.can_be_operand]) | None:
        assert len(expr.get_operands()) == 2
        lhs, rhs = expr.get_operands()

        param_in_lhs = param in mutator.utils.find_unique_params(lhs)
        param_in_rhs = param in mutator.utils.find_unique_params(rhs)

        if param_in_lhs and param_in_rhs:
            # TODO
            # supporting this situation means committing to a strategy and sticking to
            # it
            # otherwise we might just make and undo changes until we run out of
            # iterations
            return None

        assert param_in_lhs or param_in_rhs

        op_with_param = lhs if param_in_lhs else rhs
        op_without_param = rhs if param_in_lhs else lhs

        while True:
            new_op_with_param, new_op_without_param = _isolate_param(
                param,
                op_with_param.as_parameter_operatable(),
                op_without_param,
                from_expr=expr,
            )

            if new_op_with_param.is_same(
                op_with_param
            ) and new_op_without_param.is_same(op_without_param):
                break

            op_with_param, op_without_param = new_op_with_param, new_op_without_param

            if op_with_param.is_same(param.as_operand()):
                return op_with_param, op_without_param

            # TODO: check for no further progress

    exprs = mutator.get_typed_expressions(Is, sort_by_depth=True)
    for expr in exprs:
        expr_e = expr.get_trait(F.Expressions.is_expression)
        expr_po = expr.get_trait(F.Parameters.is_parameter_operatable)
        if mutator.utils.try_extract_literal(expr_po) is None:
            continue

        # TODO why? are we trying to do only arithmetic?
        # Then why not do isinstance(expr, Arithmetic)?
        if any(
            lit.equals_singleton(True) for lit in expr_e.get_operand_literals().values()
        ):
            continue

        unaliased_params = {
            p
            for p in mutator.utils.find_unique_params(expr_po.as_operand())
            if mutator.utils.try_extract_literal(p) is None
        }

        # only handle single free var
        if len(unaliased_params) != 1:
            continue

        param = unaliased_params.pop()

        if param.as_operand() in expr_e.get_operands() and not any(
            op is not param and mutator.utils.find_unique_params(op) == {param}
            for op in expr_e.get_operands()
        ):
            # already isolated
            continue

        if (result := isolate_param(expr_e, param)) is None:
            continue

        mutator.mutate_expression(expr_e, operands=result)


@algorithm("Distribute literals across alias classes", terminal=False)
def distribute_literals_across_alias_classes(mutator: Mutator):
    """
    Distribute literals across alias classes

    E is A, A is Lit -> E is Lit
    E is A, A ss Lit -> E ss Lit

    """
    for p in mutator.get_parameter_operatables():
        lit, is_alias = mutator.utils.try_extract_literal_info(p)
        if lit is None:
            continue

        non_lit_aliases = {
            e: other_p
            for e in p.get_operations(Is, predicates_only=True)
            if not e.get_trait(F.Expressions.is_expression).get_operand_literals()
            and (other_p := e.get_other_operand(p.as_operand())) is not p
        }
        for alias_expr, alias in non_lit_aliases.items():
            alias_expr_po = alias_expr.get_trait(F.Parameters.is_parameter_operatable)
            if is_alias:
                mutator.utils.alias_to(
                    alias,
                    lit.as_operand(),
                    from_ops=[p, alias_expr_po],
                )
            else:
                mutator.utils.subset_to(
                    alias,
                    lit.as_operand(),
                    from_ops=[p, alias_expr_po],
                )


# Terminal -----------------------------------------------------------------------------


@algorithm("Predicate unconstrained operands deduce", terminal=True)
def predicate_unconstrained_operands_deduce(mutator: Mutator):
    """
    A op! B | A or B unconstrained -> A op!! B
    """

    preds = mutator.get_expressions(required_traits=(F.Expressions.is_predicate,))
    for p in preds:
        if mutator.is_predicate_terminated(
            p.get_sibling_trait(F.Expressions.is_predicate)
        ):
            continue
        if mutator.utils.is_literal_expression(p.as_operand()):
            continue

        for op in p.get_operand_operatables():
            if mutator.utils.no_other_predicates(
                op,
                p.get_sibling_trait(F.Expressions.is_assertable),
                unfulfilled_only=True,
            ):
                mutator.utils.alias_is_literal_and_check_predicate_eval(
                    p, mutator.make_lit(True)
                )
                break


# Estimation algorithms ----------------------------------------------------------------
@algorithm("Upper estimation", terminal=False)
def upper_estimation_of_expressions_with_subsets(mutator: Mutator):
    """
    If any operand in an expression has a subset literal,
    we can add a subset to the expression.

    ```
    A + B | B is [1,5] -> (A + B) , (A + B) subset (A + [1,5])
    A + B | B subset [1,5] -> (A + B) , (A + B) subset (A + [1,5])
    ```

    No need to check:
    ```
    A + B | A alias B ; never happens (after eq classes)
    A + B | B alias ([0]); never happens (after aliased_single_into_literal)
    ```
    """

    new_literal_mappings = mutator.get_literal_mappings(
        new_only=True, allow_subset=True
    )
    new_exprs = {
        k: v
        for k, v in new_literal_mappings.items()
        if not mutator.utils.is_correlatable_literal(v)
    }

    exprs = {e for alias in new_exprs.keys() for e in alias.get_operations()}
    exprs.update((fabll.Traits(e).get_obj_raw() for e in mutator.non_copy_mutated))
    exprs = F.Expressions.is_expression.sort_by_depth(exprs, ascending=True)

    for expr in exprs:
        # In Is automatically by eq classes
        if expr.isinstance(F.Expressions.Is):
            continue
        expr_e = expr.get_trait(F.Expressions.is_expression)
        # Taken care of by singleton fold
        if any(
            mutator.utils.is_replacable_by_literal(op) is not None
            for op in expr_e.get_operands()
        ):
            continue
        # optimization: don't take away from uncorrelated_alias_fold
        if (
            mutator.terminal
            # not (expr in new_subsets and expr not in new_aliases)
            and not any(mutator.utils.get_correlations(expr_e))
            and mutator.utils.map_extract_literals(expr_e)[1]
        ):
            continue
        # In subset useless to look at subset lits
        no_allow_subset_lit = expr.isinstance(F.Expressions.IsSubset)

        operands, any_lit = mutator.utils.map_extract_literals(
            expr_e, allow_subset=not no_allow_subset_lit
        )
        if not any_lit:
            continue

        # TODO make this more efficient (include in extract)
        lit_alias_origins = {
            e
            for p in any_lit
            for e in p.get_operations(Is, predicates_only=True)
            if e.get_trait(F.Expressions.is_expression).get_operand_literals()
        }

        expr_po = expr.get_trait(F.Parameters.is_parameter_operatable)
        # Make new expr with subset literals
        mutator.mutate_expression(
            expr_e,
            operands=operands,
            soft_mutate=IsSubset,
            from_ops=[
                expr_po,
                *(
                    lao.get_trait(F.Parameters.is_parameter_operatable)
                    for lao in lit_alias_origins
                ),
            ],
        )


@algorithm("Uncorrelated alias fold", terminal=True)
def uncorrelated_alias_fold(mutator: Mutator):
    """
    If an operation contains only operands that are not correlated with each other,
    we can replace the operands with their corresponding literals.
    ```
    op(As), no correlations in As outside of op, len(A is Lit in As) > 0
    -> op(As) is! op(As replaced by corresponding lits)
    ```

    Terminal because relies on missing correlations.
    """

    new_literal_mappings = mutator.get_literal_mappings(new_only=True)

    # bool expr always map to singles
    new_literal_mappings_filtered = {
        k: v
        for k, v in new_literal_mappings.items()
        if not mutator.utils.is_correlatable_literal(v)
    }
    exprs = {
        e for alias in new_literal_mappings_filtered for e in alias.get_operations()
    }
    # Include mutated since last run
    exprs.update(mutator.non_copy_mutated)
    exprs = F.Expressions.is_expression.sort_by_depth(exprs, ascending=True)

    for expr in exprs:
        expr_e = expr.get_trait(F.Expressions.is_expression)
        # Taken care of by singleton fold
        if any(
            mutator.utils.is_replacable_by_literal(op) is not None
            for op in expr_e.get_operands()
        ):
            continue
        if expr.isinstance(F.Expressions.Is) and expr.try_get_trait(
            F.Expressions.is_predicate
        ):
            # TODO: definitely need to do something
            # just not the same what we do with the other types
            continue
        # TODO: we can weaken this to not replace correlated operands instead of
        #   skipping the whole expression
        # check if any correlations
        if any(mutator.utils.get_correlations(expr_e)):
            continue

        operands, any_lit = mutator.utils.map_extract_literals(expr_e)
        if not any_lit:
            continue

        # TODO make this more efficient (include in extract)
        lit_alias_origins = {
            e
            for p in any_lit
            for e in p.get_operations(Is, predicates_only=True)
            if e.get_trait(F.Expressions.is_expression).get_operand_literals()
        }

        # no point in op! is op! (always true)
        if expr.try_get_trait(F.Expressions.is_predicate):
            mutator.create_expression(
                type(expr),
                *operands,
                assert_=True,
                allow_uncorrelated=True,
                from_ops=[
                    expr.get_trait(F.Parameters.is_parameter_operatable),
                    *(
                        lao.get_trait(F.Parameters.is_parameter_operatable)
                        for lao in lit_alias_origins
                    ),
                ],
            )
            continue

        mutator.mutate_expression(
            expr_e,
            operands=operands,
            soft_mutate=Is,
            from_ops=[
                expr.get_trait(F.Parameters.is_parameter_operatable),
                *(
                    lao.get_trait(F.Parameters.is_parameter_operatable)
                    for lao in lit_alias_origins
                ),
            ],
        )
