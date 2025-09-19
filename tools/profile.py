# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
import subprocess
import sys
import tempfile
import uuid
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


def open_in_default_app(path: Path) -> None:
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        elif os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as exc:  # pragma: no cover - best effort helper
        logger.warning("Failed to open %s: %s", path, exc)


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
            open_in_default_app(png_file)

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


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def memray(
    ctx: typer.Context,
    open_report: bool = typer.Option(True, help="Open the generated flamegraph"),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Where to write the flamegraph HTML report"
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite an existing output file if present"
    ),
):
    """Profile a Python program using Memray and generate a flamegraph."""

    if not ctx.args:
        typer.echo("No command provided to profile", err=True)
        raise typer.Exit(1)

    try:
        import memray  # noqa: F401
    except ImportError:
        typer.echo(
            "Memray is not installed. Run `pip install memray` to use this command.",
            err=True,
        )
        raise typer.Exit(1)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        capture_file = temp_dir_path / "memray.bin"

        subprocess.run(
            ["python", "-m", "memray", "run", "-o", str(capture_file), *ctx.args],
            check=True,
        )

        if output is None:
            report_path = Path.cwd() / f"memray-report-{uuid.uuid4().hex}.html"
        else:
            report_path = output.expanduser().resolve()
            report_path.parent.mkdir(parents=True, exist_ok=True)

        if report_path.exists() and not force:
            typer.echo(
                f"Output file {report_path} already exists. Use --force to overwrite.",
                err=True,
            )
            raise typer.Exit(1)

        memray_cmd = [
            "python",
            "-m",
            "memray",
            "flamegraph",
            str(capture_file),
        ]

        if force:
            memray_cmd.append("-f")

        memray_cmd.extend(["-o", str(report_path)])

        subprocess.run(memray_cmd, check=True)

        typer.echo(str(report_path))

        if open_report:
            open_in_default_app(report_path)


if __name__ == "__main__":
    app()
