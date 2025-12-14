import logging

import typer

from atopile.telemetry import capture

logger = logging.getLogger(__name__)


dev_app = typer.Typer(rich_markup_mode="rich")


@dev_app.command()
@capture("cli:dev_compile_start", "cli:dev_compile_end")
def compile():
    # import will trigger compilation
    import faebryk.core.zig

    _ = faebryk.core.zig


@dev_app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
@capture("cli:dev_test_start", "cli:dev_test_end")
def test(
    ctx: typer.Context,
    ci: bool = False,
    baseline: str = typer.Option(
        None,
        "--baseline",
        "-b",
        help="Git commit hash to compare against (fetches CI report for that commit)",
    ),
):
    import sys

    from faebryk.libs.util import repo_root

    sys.path.insert(0, str(repo_root()))
    from test.runner.main import main

    args = ctx.args

    if ci:
        if "-m" in args:
            raise NotImplementedError("CI mode does not support -m")
        args.extend(["-m", "not not_in_ci and not regression and not slow"])

    main(args=args, baseline_commit=baseline)
