# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path
from typing import Callable, Iterable

from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.parameter import Expression, Is, Parameter, Predicate
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

        out += f"{header}{'-'*80}\n{ind(out_str)}\n"

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

    path.write_text(out)


def export_parameters_to_file(module: Module, path: Path):
    """Write all parameters of the given module to a file."""
    # {module_name: [{param_name: param_value}, {param_name: param_value},...]}
    parameters = dict[str, list[dict[str, Parameter]]]()

    for m in module.get_children_modules(types=Module):
        parameters[m.get_full_name(types=True).split(".", maxsplit=1)[-1]] = [
            {param.get_full_name().split(".")[-1]: param}
            for param in m.get_children(direct_only=True, types=Parameter)
        ]

    logger.info(f"Writing parameters to {path}")
    out = ""
    if path.suffix == ".txt":
        for module_name, paras in sorted(parameters.items()):
            if paras:
                out += f"{module_name}\n"
                out += "\n".join(
                    [
                        f"    {par_name}: {par_value}\n"
                        for par_dict in paras
                        for par_name, par_value in par_dict.items()
                    ]
                )
                out += "\n"
    elif path.suffix == ".md":
        out += "# Module Parameters\n"
        for module_name, paras in sorted(parameters.items()):
            if paras:
                out += f"**{module_name.replace("|","&#124;")}**\n"
                out += "| Parameter Name | Parameter Value |\n"
                out += "| --- | --- |\n"
                out += "\n".join(
                    [
                        f"| {par_name.replace("|","&#124;")} | {str(par_value).replace("|","&#124;")} |\n"  # noqa E501
                        for par_dict in paras
                        for par_name, par_value in par_dict.items()
                    ]
                )
                out += "\n"
    else:
        AssertionError(
            f"Export to file extension [{path.suffix}] not supported in {path}"
        )

    path.write_text(out)
