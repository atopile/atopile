# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import subprocess
import sys
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
    force_overwrite: bool


@typer_callback(None)
def main(
    ctx: typer.Context,
    name: str,
    template_repo_url: str = TEMPLATE_REPO_URL,
    branch: str = "main",
    target_dir: Path = Path.cwd(),
    force_overwrite: bool = False,
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
        force_overwrite,
    )


# TODO add remote option
#   to do `gh repo create --template <template> <name>`


@main.command()
def local(ctx: typer.Context, cache: bool = True):
    obj = ctx.obj

    target: Path = obj.target_dir / obj.name

    if target.exists():
        if obj.force_overwrite:
            typer.echo(f"Directory {target} already exists. Overwriting.")
            subprocess.check_output(["rm", "-rf", str(target)])
        else:
            typer.echo(f"Directory {target} already exists. Aborting.")
            raise typer.Exit(code=1)

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
    p = subprocess.Popen(
        [
            sys.executable,
            target / "scripts/setup_project.py",
            "--no-cache" if not cache else "--cache",
        ]
    )
    p.wait()
