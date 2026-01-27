# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import logging
from pathlib import Path
from typing import Callable, Iterable

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.solver.solver import Solver
from faebryk.libs.util import EquivalenceClasses, groupby, ind, typename

logger = logging.getLogger(__name__)


def parameter_alias_classes(tg: fbrk.TypeGraph) -> list[set[F.Parameters.is_parameter]]:
    full_eq = EquivalenceClasses[F.Parameters.is_parameter](
        F.Parameters.is_parameter.bind_typegraph(tg).get_instances()
    )

    is_exprs = [
        e
        for e in F.Expressions.Is.bind_typegraph(tg).get_instances()
        if e.has_trait(F.Expressions.is_predicate)
    ]

    for is_expr in is_exprs:
        params_ops = [
            op.as_parameter_operatable.force_get().as_parameter.force_get()
            for op in is_expr.is_expression.get().get_operands()
            if op.has_trait(F.Parameters.is_parameter)
        ]
        full_eq.add_eq(*params_ops)

    return full_eq.get()


def get_params_for_expr(
    expr: F.Expressions.is_expression,
) -> set[F.Parameters.is_parameter]:
    param_ops = {op for op in expr.get_operands_with_trait(F.Parameters.is_parameter)}
    expr_ops = {op for op in expr.get_operands_with_trait(F.Expressions.is_expression)}

    return param_ops | {op for e in expr_ops for op in get_params_for_expr(e)}


def parameter_dependency_classes(
    tg: fbrk.TypeGraph,
) -> list[set[F.Parameters.is_parameter]]:
    related = EquivalenceClasses[F.Parameters.is_parameter](
        F.Parameters.is_parameter.bind_typegraph(tg).get_instances()
    )

    eq_exprs = [
        e.as_expression.get()
        for e in F.Expressions.is_assertable.bind_typegraph(tg).get_instances()
        if e.has_trait(F.Expressions.is_predicate)
    ]

    for eq_expr in eq_exprs:
        params = get_params_for_expr(eq_expr)
        related.add_eq(*params)

    return related.get()


def parameter_report(tg: fbrk.TypeGraph, path: Path):
    params = F.Parameters.is_parameter.bind_typegraph(tg).get_instances()
    exprs = F.Expressions.is_expression.bind_typegraph(tg).get_instances()
    predicates = {e for e in exprs if e.has_trait(F.Expressions.is_assertable)}
    set(exprs).difference_update(predicates)
    alias_classes = parameter_alias_classes(tg)
    eq_classes = parameter_dependency_classes(tg)
    unused = [
        p
        for p in params
        if not any(
            e.has_trait(F.Expressions.is_expression)
            for e in p.as_parameter_operatable.get()
            .as_expression.force_get()
            .get_operands()
        )
    ]

    def non_empty(classes: list[set[F.Parameters.is_parameter]]):
        return [c for c in classes if len(c) > 1]

    def bound(classes: list[set[F.Parameters.is_parameter]]):
        return sum(len(c) for c in non_empty(classes))

    infostr = (
        f"{len(params)} parameters"
        f"\n    {len(non_empty(alias_classes))}({bound(alias_classes)}) alias classes"
        f"\n    {len(non_empty(eq_classes))}({bound(eq_classes)}) equivalence classes"
        f"\n    {len(unused)} unused"
        "\n"
    )
    infostr += f"{len(exprs)} expressions, {len(predicates)} predicates"

    logger.info(f"Found {infostr}")

    out = ""
    out += infostr + "\n"

    def block(
        header: str,
        f: Callable[[], str] | None = None,
        lines: list[str] | list[list[str]] | None = None,
    ):
        nonlocal out
        out_str = ""
        if f:
            out_str += f()
        if lines:
            lines = [n for n in lines if isinstance(n, str)] + [
                n for nested in lines if isinstance(nested, list) for n in nested
            ]
            out_str += "\n".join(lines)

        out += f"{header}{'-' * 80}\n{ind(out_str)}\n"

    block(
        "F.Parameters.is_parameters",
        lines=sorted([p.get_full_name(types=True) for p in params]),
    )

    block(
        "Unused",
        lines=sorted([p.get_full_name(types=True) for p in unused]),
    )

    def Eq(classes: list[set[F.Parameters.is_parameter]]):
        stream = ""
        for eq_class in classes:
            if len(eq_class) <= 1:
                continue
            stream += "\n    ".join(
                sorted([p.get_full_name(types=True) for p in eq_class])
            )
            stream += "\n"
        return stream.removesuffix("\n")

    block(
        "Fully aliased",
        f=lambda: Eq(alias_classes),
    )

    block(
        "Equivalence classes",
        f=lambda: Eq(eq_classes),
    )

    def type_group(name: str, container: Iterable):
        type_grouped = sorted(
            groupby(container, lambda x: type(x)).items(), key=lambda x: typename(x[0])
        )
        block(
            name,
            lines=[
                f"{typename(type_)}: {len(list(group))}"
                for type_, group in type_grouped
            ],
        )

    type_group("Expressions", exprs)
    type_group("Predicates", predicates)

    path.write_text(out, encoding="utf-8")


def _generate_json_parameters(
    parameters: dict[str, list[tuple[str, str]]],
) -> str:
    json_parameters = {
        module_name: {
            param_name: str(param_value) for param_name, param_value in module_params
        }
        for module_name, module_params in parameters.items()
        if module_params
    }

    return json.dumps(json_parameters, indent=2)


def _generate_md_parameters(
    parameters: dict[str, list[tuple[str, str]]],
) -> str:
    out = "# Module Parameters\n"
    out += "| Module | Parameter | Value |\n"
    out += "| --- | --- | --- |\n"
    for module_name, paras in sorted(parameters.items(), key=lambda x: x[0]):
        if paras:
            par_name, par_value = next(iter(paras))
            # First parameter of the module shows the module name
            if par_name:
                out += (
                    f"| `{module_name.replace('|', '\\|')}` | "
                    f"`{par_name.replace('|', '\\|')}` | "
                    f"`{str(par_value).replace('|', '\\|')}` |\n"
                )
                # Subsequent parameters of the same module have empty module cell
                for par_name, par_value in paras[1:]:
                    out += (
                        f"|  | "
                        f"`{par_name.replace('|', '\\|')}` | "
                        f"`{str(par_value).replace('|', '\\|')}` |\n"
                    )
    out += "\n"

    return out


def _generate_txt_parameters(
    parameters: dict[str, list[tuple[str, str]]],
) -> str:
    out = ""
    for module_name, paras in sorted(parameters.items()):
        if paras:
            out += f"{module_name}\n"
            out += "\n".join(
                [f"    {par_name}: {par_value}" for par_name, par_value in paras]
            )
            out += "\n"

    return out


def export_parameters_to_file(
    module: fabll.Node, solver: Solver, path: Path, build_id: str | None = None
):
    """
    Export the variables of the given module to file(s).

    Args:
        module: The application root node
        solver: The solver used for parameter resolution
        path: Output file path
        build_id: Build ID from server (links to build history)
    """
    from faebryk.exporters.parameters.json_parameters import write_variables_to_file

    logger.info(f"Writing JSON variables to {path}")
    write_variables_to_file(
        module, solver, path, build_id=build_id, formats=("json", "markdown", "txt")
    )
