# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import subprocess
from dataclasses import dataclass
from pathlib import Path

import typer
from faebryk.libs.tools.typer import typer_callback

TEMPLATE_REPO_URL = "https://github.com/faebryk/project-template.git"


@dataclass
class CTX:
    name: str
    template_repo_url: str
    branch: str
    target_dir: Path


@typer_callback(None)
def main(
    ctx: typer.Context,
    name: str,
    template_repo_url: str = TEMPLATE_REPO_URL,
    branch: str = "main",
    target_dir: Path = Path.cwd(),
):
    """
    Can be called like this: > faebryk project
    Or python -m faebryk project
    Or python -m faebryk.tools.project
    For help invoke command without arguments.
    """

    ctx.obj = CTX(
        name,
        template_repo_url,
        branch,
        target_dir,
    )


# TODO add remote option
#   to do `gh repo create --template <template> <name>`


@main.command()
def local(ctx: typer.Context):
    obj = ctx.obj

    target = obj.target_dir / obj.name

    # git clone
    subprocess.check_output(
        [
            "git",
            "clone",
            "--branch",
            obj.branch,
            "--",
            obj.template_repo_url,
            str(target),
        ]
    )

    # setup project
    subprocess.check_output([target / "scripts/setup_project.py"])
