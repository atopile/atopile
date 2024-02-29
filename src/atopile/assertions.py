"""
Generate a report based on assertions made in the source code.
"""

import itertools
import logging
import textwrap
from collections import ChainMap, defaultdict
from enum import Enum
from typing import Any, Iterable

import pint
import rich
from eseries import eseries
from rich.style import Style
from rich.table import Table
from scipy.optimize import minimize

from atopile import address, config, errors, instance_methods, loop_soup, telemetry
from atopile.front_end import (
    Assertion,
    Assignment,
    Expression,
    RangedValue,
    lofty,
)

log = logging.getLogger(__name__)

light_row = Style(color="bright_black")
dark_row = Style(color="white")


class AssertionStatus(Enum):
    """
    The status of an assertion.
    """

    PASSED = "[green]Passed[/]"
    FAILED = "[red]Failed[/]"
    ERROR = "[red]Error[/]"


def generate_assertion_report(build_ctx: config.BuildContext):
    """
    Generate a report based on assertions made in the source code.
    """
    table = Table(show_header=True, header_style="bold green")
    table.add_column("Status")
    table.add_column("Assertion")
    table.add_column("Numeric")
    table.add_column("Address")
    table.add_column("Notes")

    rows = 0

    def _add_row(
        status: AssertionStatus,
        assertion_str: str,
        numeric: str,
        addr: address.AddrStr,
        notes: str,
    ):
        nonlocal rows
        table.add_row(
            status.value,
            assertion_str,
            numeric,
            address.get_instance_section(addr),
            notes,
            style=dark_row if rows % 2 else light_row,
        )
        rows += 1

    context = {}
    for instance_addr in instance_methods.all_descendants(build_ctx.entry):
        instance = lofty.get_instance(instance_addr)
        for assertion in instance.assertions:
            try:
                telemetry.log_assertion(str(assertion))
            except Exception as e:
                log.debug("Failed to log assertion: %s", e)
            new_symbols = {
                s.key for s in assertion.lhs.symbols | assertion.rhs.symbols
            } - context.keys()
            for symbol in new_symbols:
                parent_inst = instance_methods.get_instance(
                    address.get_parent_instance_addr(symbol)
                )
                assign_name = address.get_name(symbol)

                if assign_name not in parent_inst.assignments:
                    raise errors.AtoKeyError(
                        f"No attribute '{assign_name}' bound on '{parent_inst.addr}'"
                    )

                assignment = parent_inst.assignments[assign_name][0]
                if assignment.value is None:
                    raise errors.AtoTypeError(
                        f"'{symbol}' is defined, but has no value"
                    )
                context[symbol] = assignment.value

            try:
                a = assertion.lhs(context)
                b = assertion.rhs(context)
            except errors.AtoError as e:
                _add_row(
                    AssertionStatus.ERROR, str(assertion), "", instance_addr, str(e)
                )
                raise

            if _do_op(a, assertion.operator, b):
                status = AssertionStatus.PASSED
            else:
                status = AssertionStatus.FAILED

            numeric = a.pretty_str() + " " + assertion.operator + " " + b.pretty_str()

            _add_row(status, str(assertion), numeric, instance_addr, "")

    rich.print(table)


def _do_op(a: RangedValue, op: str, b: RangedValue) -> bool:
    """Perform the operation specified by the operator."""
    if op == "within":
        return a.within(b)
    elif op == "<":
        return a < b
    elif op == ">":
        return a > b
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
        raise errors.AtoTypeError(
            f"Dimensionality mismatch in assertion: {assertion}"
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
            with error_collector():
                # Bucket new symbols into variables and constants
                assertion_symbols = {
                    s.key for s in assertion.lhs.symbols | assertion.rhs.symbols
                }
                new_symbols = assertion_symbols - referenced_symbols
                referenced_symbols |= new_symbols
                for symbol in new_symbols:
                    parent_inst = instance_methods.get_instance(
                        address.get_parent_instance_addr(symbol)
                    )
                    assign_name = address.get_name(symbol)

                    if assign_name not in parent_inst.assignments:
                        raise errors.AtoKeyError(
                            f"No attribute '{assign_name}' bound on '{parent_inst.addr}'"
                        )

                    assignment = parent_inst.assignments[assign_name][0]
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
                else:
                    raise errors.AtoError(
                        msg,
                        title=title,
                    )

            # Here we're attempting to shuffle the values into eseries
            result_means = [
                (result.x[i * 2] + result.x[i * 2 + 1]) / 2 for i in range(len(group_vars))
            ]
            for r_vals in itertools.product(
                *[eseries.find_nearest_few(eseries.E96, x_val) for x_val in result_means],
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
                    Assignment(name, value=val, given_type="None")
                )

    # Solved for assertion values
    log.info("Values for solved variables:")
    rich.print(table)


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
    def lower_than(a: Expression, b: Expression) -> list[dict]:
        def _brrr(x):
            ctx = translator(x)
            return (
                b(ctx).min_qty.to_base_units().magnitude
                - a(ctx).max_qty.to_base_units().magnitude
            )

        return [
            {"type": "ineq", "fun": _brrr},
        ]

    def greater_than(a: Expression, b: Expression) -> list[dict]:
        def _brrr(x):
            ctx = translator(x)
            return (
                a(ctx).min_qty.to_base_units().magnitude
                - b(ctx).max_qty.to_base_units().magnitude
            )

        return [
            {"type": "ineq", "fun": _brrr},
        ]

    def within(a: Expression, b: Expression) -> list[dict]:
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

    elif assertion.operator == "within":
        return within(assertion.lhs, assertion.rhs)

    raise ValueError(f"Unknown operator {assertion.operator}")
