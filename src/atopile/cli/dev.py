import logging
from pathlib import Path

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
        help="Compare against a baseline: commit hash, or number of commits back (e.g. 3)",  # noqa: E501
    ),
    direct: bool = False,
    test_name: str | None = typer.Option(None, "-k", help="Test name pattern"),
):
    import sys

    from faebryk.libs.util import repo_root

    sys.path.insert(0, str(repo_root()))

    if direct:
        from test.runtest import logger as runtest_logger
        from test.runtest import run

        runtest_logger.setLevel(logging.INFO)

        if not test_name:
            raise ValueError("Test name is required when running directly")

        run(test_name=test_name, filepaths=[Path("test"), Path("src")])
        return

    from test.runner.main import main

    args = ctx.args

    if ci:
        if "-m" in args:
            raise NotImplementedError("CI mode does not support -m")
        args.extend(["-m", "not not_in_ci and not regression and not slow"])
    if test_name:
        args.extend(["-k", test_name])

    # Convert number to HEAD~N format (e.g. "3" -> "HEAD~3")
    baseline_commit = baseline
    if baseline is not None:
        # Check if it's a plain number
        try:
            n = int(baseline)
            if n > 0:
                baseline_commit = f"HEAD~{n}"
        except ValueError:
            pass  # Not a number, use as-is

    main(args=args, baseline_commit=baseline_commit)
