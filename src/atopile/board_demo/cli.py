from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer


def demo(
    entry: Annotated[str | None, typer.Argument()] = None,
    build: Annotated[list[str], typer.Option("--build", "-b", envvar="ATO_BUILD")] = [],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output directory for the generated demo bundle",
        ),
    ] = None,
    no_validate: Annotated[
        bool,
        typer.Option(
            "--no-validate",
            help="Validate the demo bundle with Puppeteer",
        ),
    ] = False,
    stats: Annotated[
        bool,
        typer.Option(
            "--stats",
            help="Show FPS and renderer stats overlay in the 3D viewer",
        ),
    ] = False,
) -> None:
    """
    Generate a static demo bundle for a single build target.
    """
    from atopile.board_demo.artifacts import DemoBundleBuilder
    from atopile.config import config

    config.apply_options(
        entry=entry,
        selected_builds=build if build else (),
    )

    build_names = list(config.selected_builds)
    if len(build_names) != 1:
        raise typer.BadParameter(
            "ato demo requires exactly one selected build target; use -b <build>"
        )

    build_name = build_names[0]
    with config.select_build(build_name):
        builder = DemoBundleBuilder(
            output_dir=output, validate=not no_validate, show_stats=stats
        )
        builder.build()
