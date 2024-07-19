"""
Generate a report based on assertions made in the source code.
"""

import itertools
import logging
import textwrap
from collections import ChainMap, defaultdict
from typing import Any, Iterable

import pint
import rich
from eseries import eseries
from rich.style import Style
from rich.table import Table
from scipy.optimize import minimize

from atopile import (
    address,
    config,
    errors,
    expressions,
    instance_methods,
    loop_soup,
    parse_utils,
    telemetry,
)
from atopile.front_end import Assertion, Assignment, RangedValue, lofty

log = logging.getLogger(__name__)

light_row = Style(color="bright_black")
dark_row = Style(color="white")


def _try_log_assertion(assertion):
    try:
        telemetry.log_assertion(str(assertion))
    except Exception as e:
        log.debug("Failed to log assertion: %s", e)


class AssertionException(errors.AtoError):
    """An exception raised when an assertion fails."""


class AssertionFailed(AssertionException):
    """An exception raised when an assertion fails."""


class ErrorComputingAssertion(AssertionException):
    """An exception raised when an exception is
    raised while trying to compute an assertion's
    values."""


class AssertionTable(Table):
    def __init__(self) -> None:
        super().__init__(show_header=True, header_style="bold green", title="Assertions")

        self.add_column("Status")
        self.add_column("Assertion")
        self.add_column("Numeric")

    def add_row(
        self,
        status: str,
        assertion_str: str,
        numeric: str,
    ):
        super().add_row(
            status,
            assertion_str,
            numeric,
            style=dark_row if len(self.rows) % 2 else light_row,
        )


def generate_assertion_report(build_ctx: config.BuildContext):
    """
    Generate a report based on assertions made in the source code.
    """

    table = AssertionTable()
    context = {}
    with errors.ExceptionAccumulator() as exception_accumulator:
        for instance_addr in instance_methods.all_descendants(build_ctx.entry):
            instance = lofty.get_instance(instance_addr)
            for assertion in instance.assertions:
                with exception_accumulator():
                    _try_log_assertion(assertion)

                    # Build the context in which to evaluate the assertion
                    new_symbols = {
                        s.key for s in assertion.lhs.symbols | assertion.rhs.symbols
                    } - context.keys()

                    for symbol in new_symbols:
                        context[symbol] = instance_methods.get_data(symbol)

                    for symbol in assertion.lhs.symbols | assertion.rhs.symbols:
                        assert symbol.key in context, f"Symbol {symbol} not found in context"

                    assertion_str = parse_utils.reconstruct(assertion.src_ctx)

                    instance_src = instance_addr
                    if instance.src_ctx:
                        instance_src += "\n (^ defined" + parse_utils.format_src_info(instance.src_ctx) + ")"

                    try:
                        a = assertion.lhs(context)
                        b = assertion.rhs(context)
                        passes = _do_op(a, assertion.operator, b)
                    except (errors.AtoError, KeyError, pint.DimensionalityError) as e:
                        table.add_row(
                            "[red]ERROR[/]",
                            assertion_str,
                            "",
                        )
                        raise ErrorComputingAssertion(
                            f"Exception computing assertion: {e.__class__.__name__} {str(e)}"
                        ) from e

                    assert isinstance(a, RangedValue)
                    assert isinstance(b, RangedValue)
                    numeric = (
                        a.pretty_str(format_="bound") +
                        " " + assertion.operator +
                        " " + b.pretty_str(format_="bound")
                    )
                    if passes:
                        table.add_row(
                            "[green]PASSED[/]",
                            assertion_str,
                            numeric,
                        )
                        log.debug(
                            textwrap.dedent(f"""
                                Assertion [green]passed![/]
                                address: {instance_addr}
                                assertion: {assertion_str}
                                numeric: {numeric}
                            """).strip(),
                            extra={"markup": True}
                        )
                    else:
                        table.add_row(
                            "[red]FAILED[/red]",
                            assertion_str,
                            numeric,
                        )
                        raise AssertionFailed.from_ctx(
                            assertion.src_ctx,
                            textwrap.dedent(f"""
                                address: $addr
                                assertion: {assertion_str}
                                numeric: {numeric}
                            """).strip(),
                            addr=instance_addr,
                        )

        # Dump the output to the console
        rich.print(table)


def _do_op(a: RangedValue, op: str, b: RangedValue) -> bool:
    """Perform the operation specified by the operator."""
    if op == "within":
        return a.within(b)
    elif op == "<":
        return a < b
    elif op == ">":
        return a > b
    elif op == "<=":
        return a <= b
    elif op == ">=":
        return a >= b
    else:
        raise ValueError(f"Unrecognized operator: {op}")


def _check_assertion(assertion: Assertion, context: dict) -> bool:
    """
    Check if an assertion is true in the given context.
    """
    try:
        a = assertion.lhs(context)
        b = assertion.rhs(context)
        return _do_op(a, assertion.operator, b)
    except pint.errors.DimensionalityError as ex:
        if assertion.src_ctx:
            raise errors.AtoTypeError.from_ctx(
                assertion.src_ctx,
                f"Dimensionality mismatch in assertion"
                f" ({ex.units1} incompatible with {ex.units2})"
            ) from ex
        raise errors.AtoTypeError(
            f"Dimensionality mismatch in assertion"
            f" ({ex.units1} incompatible with {ex.units2})"
        ) from ex


def solve_assertions(build_ctx: config.BuildContext):
    """
    Solve the assertions in the build context.
    FIXME:
        - This mutates the instances
    """

    # 1. Find all the symbols referenced in assertions in the design
    # ... and figure out which are variables and which are fixed
    referenced_symbols: set[address.AddrStr] = set()
    constants: dict[address.AddrStr, Any] = {}
    variable_units: dict[str, pint.Unit] = {}
    variable_soup = loop_soup.LoopSoup()
    for error_collector, instance_addr in errors.iter_through_errors(
        instance_methods.all_descendants(build_ctx.entry)
    ):
        instance = lofty.get_instance(instance_addr)
        for assertion in instance.assertions:
            with error_collector(assertion.src_ctx):
                # Bucket new symbols into variables and constants
                assertion_symbols = {
                    s.key for s in assertion.lhs.symbols | assertion.rhs.symbols
                }
                new_symbols = assertion_symbols - referenced_symbols
                referenced_symbols |= new_symbols
                for symbol in new_symbols:
                    assignment = instance_methods.get_assignments(symbol)[0]
                    if assignment.value is None:
                        # TEMP: this is in place because our discretization strategy
                        # requires E96 things
                        if not assignment.unit.is_compatible_with(pint.Unit("ohm")):
                            raise errors.AtoTypeError.from_ctx(
                                assignment.src_ctx,
                                f"'{symbol}' is defined, but has no value.\n"
                                "Currently the calculator only supports resistor "
                                "values, so please assign a value to this attribute.",
                            )
                        variable_units[symbol] = assignment.unit
                        variable_soup.add(symbol)
                    else:
                        constants[symbol] = assignment.value

                # Group up all the entangled symbols
                variable_soup.join_multiple(
                    filter(lambda s: s in variable_soup, assertion_symbols)
                )

    # If there isn't anything to solve, just return
    if not variable_soup:
        log.info("No variables in assertions to solve")
        return

    vars = list(variable_soup)
    try:
        telemetry.log_eqn_vars(len(vars))
    except Exception as e:
        log.debug("Failed to log eqn_vars: %s", e)
    log.debug("Variables to solve for: %s", vars)

    # 2. Create groups of assertions based on the symbols they contain
    # This way we don't need to solve for every assertion at once
    assertion_groups: dict[tuple[address.AddrStr], list[dict]] = defaultdict(list)
    for instance_addr in instance_methods.all_descendants(build_ctx.entry):
        instance = lofty.get_instance(instance_addr)
        for assertion in instance.assertions:
            for symbol in assertion.lhs.symbols | assertion.rhs.symbols:
                # Only add the constraint if the assertion contains a variable
                # Otherwise, this assertion isn't relevant to the optimization
                if symbol.key in variable_soup:
                    group_key = tuple(
                        sorted(variable_soup.get_loop(symbol.key).iter_values())
                    )
                    assertion_groups[group_key].append(assertion)
                    break  # onto the next assertion

    # 3. Solve each group
    table = Table(show_header=True, header_style="bold green")
    table.add_column("Address")
    table.add_column("Value")
    row_count = 0

    for error_collector, assertion_group in errors.iter_through_errors(assertion_groups.items()):
        group_vars, assertions = assertion_group
        with error_collector():
            log.debug("Solving for group %s", group_vars)
            translator = _translator_factory(
                group_vars, [variable_units[addr] for addr in group_vars], constants
            )

            constraints = [
                c for a in assertions for c in _constraint_factory(a, translator)
            ]

            result = minimize(
                # FIXME: see notes in _cost about how stupid this function is
                _cost,
                # FIXME: this single starting points is medicore at best
                tuple(v + 10 for v in range(len(group_vars) * 2)),
                constraints=constraints,
                # FIXME: this should have bounds, but they'll depend on the variable's constraints
                # We could perhaps inherit these from the variable's type?
                bounds=[(0, None)] * len(group_vars) * 2,
                options={
                    "disp": log.getEffectiveLevel() <= logging.DEBUG,
                    "maxiter": 1000,
                },
            )
            log.debug("Optimization result: %s", result)
            if not result.success:
                title = f"Failed to solve assertions: {result.message}"
                msg = textwrap.dedent(
                    """
                    The optimization algorithm failed to find a solution.
                    This could mean a litany of things went wrong, but most likely:
                    - The constraints are backwards / too tight
                    - Variables are missing tolerances
                    - Assertions conflict with one another
                    """
                )

                msg += "\n\nVariables:\n"
                for v in group_vars:
                    msg += f"  {v}\n"
                    assignment_origin = instance_methods.get_assignments(v)[0].src_ctx
                    msg += f"    (^ assigned {parse_utils.format_src_info(assignment_origin)})\n\n"

                if constants:
                    msg += "\n\nConstants:\n"
                    for c, v in constants.items():
                        msg += f"  {c} = {v}\n"

                msg += "\n\nAssertions:\n"
                for a in assertions:
                    if hasattr(a, "src_ctx") and a.src_ctx:
                        msg += f"  {parse_utils.reconstruct(a.src_ctx)}\n"
                    else:
                        msg += "  Unknown Source\n"

                if (
                    len(assertions) == 1
                    and hasattr(assertions[0], "src_ctx")
                    and assertions[0].src_ctx
                ):
                    raise errors.AtoError.from_ctx(
                        assertions[0].src_ctx,
                        title=title,
                        message=msg,
                    )

                raise errors.AtoError(
                    msg,
                    title=title,
                )

            # Here we're attempting to shuffle the values into eseries
            result_means = [
                (result.x[i * 2] + result.x[i * 2 + 1]) / 2
                for i in range(len(group_vars))
            ]
            for r_vals in itertools.product(
                *[
                    eseries.find_nearest_few(eseries.E96, x_val)
                    for x_val in result_means
                ],
                repeat=1,
            ):
                final_values = [
                    v
                    for r_val in r_vals
                    for v in [
                        r_val - 1.1 * r_val * eseries.tolerance(eseries.E96),
                        r_val + 1.1 * r_val * eseries.tolerance(eseries.E96),
                    ]
                ]
                _context = translator(final_values)
                if all(_check_assertion(a, _context) for a in assertions):
                    break
            else:
                raise errors.AtoError(
                    "Failed to find a solution that satisfies all the assertions using e96 values",
                    title="Failed to solve assertions",
                )

            # Apply the values back to the model
            for i, addr in enumerate(group_vars):
                parent = lofty.get_instance(address.get_parent_instance_addr(addr))
                name = address.get_name(addr)

                val = RangedValue(
                    final_values[i * 2], final_values[i * 2 + 1], variable_units[addr]
                )

                table.add_row(
                    address.get_instance_section(addr),
                    str(val),
                    style=dark_row if row_count % 2 else light_row,
                )
                row_count += 1

                # FIXME: Do we want to mutate the model here?
                # FIXME: Creating Assignment object here is annoying
                parent.assignments[name].appendleft(
                    Assignment(name, value=val, given_type="None", value_is_derived=True)
                )

    # Solved for assertion values
    log.info("Values for solved variables:")
    rich.print(table)


def simplify_expressions(entry_addr: address.AddrStr):
    """
    Simplify the expressions in the build context.
    """

    # Build the context to simplify everything on
    # FIXME: I hate that we're iterating over the whole model, to grab
    # all the context all at once and duplicated it into a dict.
    context: dict[str, expressions.NumericishTypes] = {}
    for instance_addr in instance_methods.all_descendants(entry_addr):
        instance = lofty.get_instance(instance_addr)
        for assignment_key, assignment in instance.assignments.items():
            if assignment and assignment[0].value is not None:
                context[address.add_instance(instance_addr, assignment_key)] = (
                    assignment[0].value
                )

    # Simplify the expressions
    simplified = expressions.simplify_expression_pool(context)

    # Update the model with simplified expressions
    for addr, value in simplified.items():
        parent_addr = address.get_parent_instance_addr(addr)
        name = address.get_name(addr)
        parent_instance = lofty.get_instance(parent_addr)
        parent_instance.assignments[name].appendleft(
            Assignment(name, value=value, given_type=None, value_is_derived=True)
        )

    # Great, now simplify the expressions in the assertions
    # TODO:
    simplified_context = {**context, **simplified}
    for instance_addr in instance_methods.all_descendants(entry_addr):
        instance = lofty.get_instance(instance_addr)
        for assertion in instance.assertions:
            assertion.lhs = expressions.Expression.from_numericish(
                expressions.simplify_expression(assertion.lhs, simplified_context)
            )
            assertion.rhs = expressions.Expression.from_numericish(
                expressions.simplify_expression(assertion.rhs, simplified_context)
            )


def _translator_factory(
    args: Iterable, arg_units: Iterable[pint.Unit], known_context: dict
):
    assert len(args) == len(arg_units)

    def _translate(x):
        assert len(x) == len(args) * 2
        arg_ctx = {
            arg: RangedValue(x[i * 2], x[i * 2 + 1], arg_units[i])
            for i, arg in enumerate(args)
        }
        return ChainMap(arg_ctx, known_context)

    return _translate


def _tolerance_cost(min_: float, max_: float):
    if min_ == max_:
        return 1e4
    mean = (min_ + max_) / 2
    if mean == 0:
        return 1 / (100 * (max_ - min_)) ** 2
    return 1 / (100 * (max_ - min_) / mean) ** 2


def _cost(x):
    """
    Works under the assumption that x is paired up ranged values
    FIXME:
        - This assumption of tolerance having cost breaks for variables
        you'd expect to expand into one another, eg. v_in of a vdiv used.
        for feedback on a reg or i_q for it's quiescent current. This
        manifests as squeezing the resistors' tolerances down, which means
        we frequently can't find any that actually fit.
    """
    return sum(
        _tolerance_cost(x[i * 2], x[i * 2 + 1]) for i in range(len(x) // 2)
    ) / len(x)


def _constraint_factory(assertion: Assertion, translator):
    def lower_than(a: expressions.Expression, b: expressions.Expression) -> list[dict]:
        def _brrr(x):
            ctx = translator(x)
            return (
                b(ctx).min_qty.to_base_units().magnitude
                - a(ctx).max_qty.to_base_units().magnitude
            ) or -1  # To make 0 exclusive

        return [
            {"type": "ineq", "fun": _brrr},
        ]

    def greater_than(a: expressions.Expression, b: expressions.Expression) -> list[dict]:
        def _brrr(x):
            ctx = translator(x)
            return (
                a(ctx).min_qty.to_base_units().magnitude
                - b(ctx).max_qty.to_base_units().magnitude
            ) or -1  # To make 0 exclusive

        return [
            {"type": "ineq", "fun": _brrr},
        ]

    def lower_than_eq(a: expressions.Expression, b: expressions.Expression) -> list[dict]:
        def _brrr(x):
            ctx = translator(x)
            return (
                b(ctx).min_qty.to_base_units().magnitude
                - a(ctx).max_qty.to_base_units().magnitude
            )

        return [
            {"type": "ineq", "fun": _brrr},
        ]

    def greater_than_eq(a: expressions.Expression, b: expressions.Expression) -> list[dict]:
        def _brrr(x):
            ctx = translator(x)
            return (
                a(ctx).min_qty.to_base_units().magnitude
                - b(ctx).max_qty.to_base_units().magnitude
            )

        return [
            {"type": "ineq", "fun": _brrr},
        ]

    def within(a: expressions.Expression, b: expressions.Expression) -> list[dict]:
        def _brrr(x):
            ctx = translator(x)
            return (
                b(ctx).max_qty.to_base_units().magnitude
                - a(ctx).max_qty.to_base_units().magnitude
            )

        def _brrr2(x):
            ctx = translator(x)
            return (
                a(ctx).min_qty.to_base_units().magnitude
                - b(ctx).min_qty.to_base_units().magnitude
            )

        return [
            {"type": "ineq", "fun": _brrr},
            {"type": "ineq", "fun": _brrr2},
        ]

    if assertion.operator == "<":
        return lower_than(assertion.lhs, assertion.rhs)

    elif assertion.operator == ">":
        return greater_than(assertion.lhs, assertion.rhs)

    elif assertion.operator == "<=":
        return lower_than(assertion.lhs, assertion.rhs)

    elif assertion.operator == ">=":
        return greater_than(assertion.lhs, assertion.rhs)

    elif assertion.operator == "within":
        return within(assertion.lhs, assertion.rhs)

    raise ValueError(f"Unknown operator {assertion.operator}")
