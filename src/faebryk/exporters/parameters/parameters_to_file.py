# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import json
import logging
from pathlib import Path
from typing import Any, Callable, Iterable

from atopile.errors import UserBadParameterError
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.parameter import Expression, Is, Parameter, Predicate
from faebryk.core.solver.solver import Solver
from faebryk.libs.sets.sets import P_Set
from faebryk.libs.util import EquivalenceClasses, groupby, ind, typename

logger = logging.getLogger(__name__)


def parameter_alias_classes(G: Graph) -> list[set[Parameter]]:
    full_eq = EquivalenceClasses[Parameter](GraphFunctions(G).nodes_of_type(Parameter))

    is_exprs = [e for e in GraphFunctions(G).nodes_of_type(Is) if e.constrained]

    for is_expr in is_exprs:
        params_ops = [op for op in is_expr.operands if isinstance(op, Parameter)]
        full_eq.add_eq(*params_ops)

    return full_eq.get()


def get_params_for_expr(expr: Expression) -> set[Parameter]:
    param_ops = {op for op in expr.operatable_operands if isinstance(op, Parameter)}
    expr_ops = {op for op in expr.operatable_operands if isinstance(op, Expression)}

    return param_ops | {op for e in expr_ops for op in get_params_for_expr(e)}


def parameter_dependency_classes(G: Graph) -> list[set[Parameter]]:
    related = EquivalenceClasses[Parameter](GraphFunctions(G).nodes_of_type(Parameter))

    eq_exprs = [e for e in GraphFunctions(G).nodes_of_type(Predicate) if e.constrained]

    for eq_expr in eq_exprs:
        params = get_params_for_expr(eq_expr)
        related.add_eq(*params)

    return related.get()


def parameter_report(G: Graph, path: Path):
    params = GraphFunctions(G).nodes_of_type(Parameter)
    exprs = GraphFunctions(G).nodes_of_type(Expression)
    predicates = {e for e in exprs if isinstance(e, Predicate)}
    exprs.difference_update(predicates)
    alias_classes = parameter_alias_classes(G)
    eq_classes = parameter_dependency_classes(G)
    unused = [
        p
        for p in params
        if not any(isinstance(e.node, Expression) for e in p.operated_on.edges)
    ]

    def non_empty(classes: list[set[Parameter]]):
        return [c for c in classes if len(c) > 1]

    def bound(classes: list[set[Parameter]]):
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
        "Parameters",
        lines=sorted([p.get_full_name(types=True) for p in params]),
    )

    block(
        "Unused",
        lines=sorted([p.get_full_name(types=True) for p in unused]),
    )

    def Eq(classes: list[set[Parameter]]):
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


def _generate_json_parameters(parameters: dict[str, dict[str, P_Set[Any]]]) -> str:
    json_parameters = {
        module_name: {
            param_name: str(param_value)
            for param_name, param_value in module_params.items()
        }
        for module_name, module_params in parameters.items()
        if module_params
    }

    return json.dumps(json_parameters, indent=2)


def _generate_md_parameters(parameters: dict[str, dict[str, P_Set[Any]]]) -> str:
    out = "# Module Parameters\n"
    out += "| Module | Parameter | Value |\n"
    out += "| --- | --- | --- |\n"
    for module_name, paras in sorted(parameters.items()):
        if paras:
            # Sort parameters for consistent output
            sorted_params = sorted(paras.items())
            # First parameter of the module shows the module name
            if sorted_params:
                par_name, par_value = sorted_params[0]
                out += (
                    f"| `{module_name.replace('|', '\\|')}` | "
                    f"`{par_name.replace('|', '\\|')}` | "
                    f"`{str(par_value).replace('|', '\\|')}` |\n"
                )
                # Subsequent parameters of the same module have empty module cell
                for par_name, par_value in sorted_params[1:]:
                    out += (
                        f"|  | "
                        f"`{par_name.replace('|', '\\|')}` | "
                        f"`{str(par_value).replace('|', '\\|')}` |\n"
                    )
    out += "\n"

    return out


def _generate_txt_parameters(parameters: dict[str, dict[str, P_Set[Any]]]) -> str:
    out = ""
    for module_name, paras in sorted(parameters.items()):
        if paras:
            out += f"{module_name}\n"
            out += "\n".join(
                [
                    f"    {par_name}: {par_value}\n"
                    for par_name, par_value in paras.items()
                ]
            )
            out += "\n"

    return out


def export_parameters_to_file(module: Module, solver: Solver, path: Path):
    """Write all parameters of the given module to a file."""
    # {module_name: [{param_name: param_value}, {param_name: param_value},...]}

    parameters = dict[str, dict[str, P_Set[Any]]]()

    for m in module.get_children_modules(types=Module, include_root=True):
        module_name = m.get_full_name(types=True)
        module_params = m.get_children(
            direct_only=True, include_root=True, types=Parameter
        )
        param_names = [param.get_full_name().split(".")[-1] for param in module_params]
        param_values = [
            solver.inspect_get_known_supersets(param) for param in module_params
        ]
        parameters[module_name] = {
            name: value for name, value in zip(param_names, param_values)
        }

    logger.info(f"Writing parameters to {path}")

    match path.suffix:
        case ".txt":
            out = _generate_txt_parameters(parameters)
        case ".md":
            out = _generate_md_parameters(parameters)
        case ".json":
            out = _generate_json_parameters(parameters)
        case _:
            raise UserBadParameterError(
                f"Export to file extension [{path.suffix}] not supported in {path}"
            )

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    try:
        temp_path.write_text(out, encoding="utf-8")
        temp_path.replace(path)
    finally:
        if temp_path.exists():
            temp_path.unlink()
