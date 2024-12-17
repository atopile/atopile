# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
import subprocess
import tempfile
from pathlib import Path

import typer

logger = logging.getLogger(__name__)
app = typer.Typer()


def is_running_in_vscode_terminal() -> bool:
    return (
        "TERM_PROGRAM" in os.environ and "vscode" in os.environ["TERM_PROGRAM"].lower()
    )


def get_vscode_instances_count(binname: str) -> int:
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        return len(
            [
                line
                for line in result.stdout.splitlines()
                if f"/{binname}" in line and "grep" not in line
            ]
        )
    except subprocess.SubprocessError:
        return 0


def get_code_binary() -> Path | None:
    candidates = ["cursor", "code"]
    for candidate in candidates:
        result = subprocess.run(["which", candidate], capture_output=True, text=True)
        if result.returncode == 0:
            return Path(result.stdout.strip())
    return None


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def cprofile(
    ctx: typer.Context, snakeviz: bool = typer.Option(False, help="Use snakeviz")
):
    """Profile a Python program using cProfile."""
    if not ctx.args:
        typer.echo("No command provided to profile", err=True)
        raise typer.Exit(1)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        pstats_file = temp_dir_path / "output.pstats"
        dot_file = temp_dir_path / "output.dot"

        # Run cProfile
        subprocess.run(
            ["python", "-m", "cProfile", "-o", str(pstats_file), *ctx.args], check=True
        )

        # Convert to dot format
        subprocess.run(
            ["gprof2dot", "-f", "pstats", str(pstats_file), "-o", str(dot_file)],
            check=True,
        )

        # Determine how to display the output
        code_bin = get_code_binary()

        if is_running_in_vscode_terminal():
            subprocess.run(["code", str(dot_file)], check=True)
        elif code_bin and get_vscode_instances_count(code_bin.name) > 0:
            subprocess.run([str(code_bin), "-r", str(dot_file)], check=True)
        else:
            png_file = temp_dir_path / "output.png"
            subprocess.run(
                ["dot", "-Tpng", "-o", str(png_file), str(dot_file)], check=True
            )
            subprocess.Popen(["xdg-open", str(png_file)])

        if snakeviz:
            subprocess.run(["snakeviz", str(pstats_file)], check=True)

        # Display with cursor
        typer.echo(str(dot_file))


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def viztracer(ctx: typer.Context):
    """Profile a Python program using VizTracer."""
    if not ctx.args:
        typer.echo("No command provided to profile", err=True)
        raise typer.Exit(1)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        json_file = temp_dir_path / "output.json"
        subprocess.run(
            ["viztracer", "--open", "-o", str(json_file), *ctx.args], check=True
        )


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def pyinstrument(ctx: typer.Context):
    """Profile a Python program using Pyinstrument."""
    if not ctx.args:
        typer.echo("No command provided to profile", err=True)
        raise typer.Exit(1)

    subprocess.run(["pyinstrument", "-r", "text", *ctx.args], check=True)


if __name__ == "__main__":
    app()
