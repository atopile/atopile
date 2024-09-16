# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

from faebryk.core.module import Module
from faebryk.core.parameter import Parameter

logger = logging.getLogger(__name__)


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
