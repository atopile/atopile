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
        e.as_expression()
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
    parameters: dict[str, dict[str, F.Literals.is_literal]],
) -> str:
    json_parameters = {
        module_name: {
            param_name: str(param_value)
            for param_name, param_value in module_params.items()
        }
        for module_name, module_params in parameters.items()
        if module_params
    }

    return json.dumps(json_parameters, indent=2)


def _generate_md_parameters(
    parameters: dict[str, dict[str, F.Literals.is_literal]],
) -> str:
    out = "# Module F.Parameters.is_parameters\n"
    out += "| Module | F.Parameters.is_parameter | Value |\n"
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


def _generate_txt_parameters(
    parameters: dict[str, dict[str, F.Literals.is_literal]],
) -> str:
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


def export_parameters_to_file(module: fabll.Node, solver: Solver, path: Path):
    """Write all parameters of the given module to a file."""
    # {module_name: [{param_name: param_value}, {param_name: param_value},...]}

    parameters = dict[str, dict[str, F.Literals.is_literal]]()

    for m in module.get_children(
        direct_only=False,
        types=fabll.Node,
        required_trait=fabll.is_module,
        include_root=True,
    ):
        module_name = m.get_full_name(types=True)
        module_params = m.get_children(
            direct_only=True,
            types=fabll.Node,
            include_root=True,
            required_trait=F.Parameters.is_parameter,
        )
        param_names = [param.get_full_name().split(".")[-1] for param in module_params]
        param_values = [
            solver.inspect_get_known_supersets(
                param.get_trait(F.Parameters.is_parameter)
            )
            for param in module_params
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
            raise ValueError(
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
