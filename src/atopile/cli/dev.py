import json
import logging
import subprocess
import tempfile
import webbrowser
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


def _fetch_and_open_test_report(commit_hash: str) -> None:
    """
    Fetch the test-report.html artifact from GitHub Actions for the given commit
    and open it in the default browser.
    """
    # Resolve short hash to full hash using git
    try:
        result = subprocess.run(
            ["git", "rev-parse", commit_hash],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            full_hash = result.stdout.strip()
            short_hash = full_hash[:8]
        else:
            full_hash = commit_hash
            short_hash = commit_hash[:8] if len(commit_hash) >= 8 else commit_hash
    except Exception:
        full_hash = commit_hash
        short_hash = commit_hash[:8] if len(commit_hash) >= 8 else commit_hash

    typer.echo(f"Fetching test report for commit {short_hash}...")

    # Check gh CLI is available
    try:
        result = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            typer.secho(
                "Failed to get repository info. "
                "Is `gh` CLI installed and authenticated?",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)
    except FileNotFoundError:
        typer.secho(
            "gh CLI not found. Install with: brew install gh",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(f"Error checking gh CLI: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Find the workflow run for this commit
    try:
        result = subprocess.run(
            [
                "gh",
                "run",
                "list",
                "--commit",
                full_hash,
                "--workflow",
                "pytest.yml",
                "--status",
                "completed",
                "--limit",
                "1",
                "--json",
                "databaseId,headSha,headBranch,conclusion",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            typer.secho(
                f"Failed to find workflow run: {result.stderr}",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)

        runs = json.loads(result.stdout)
        if not runs:
            typer.secho(
                f"No completed pytest workflow run found for commit '{short_hash}'",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)

        run_id = runs[0]["databaseId"]
        branch = runs[0].get("headBranch", "unknown")
        conclusion = runs[0].get("conclusion", "unknown")

        typer.echo(
            f"Found run {run_id} on branch '{branch}' (conclusion: {conclusion})"
        )

    except json.JSONDecodeError as e:
        typer.secho(f"Failed to parse workflow run response: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Download the HTML report artifact to a temp directory
    # We use a named temp file that persists so the browser can access it
    temp_dir = tempfile.mkdtemp(prefix="ato-test-report-")
    temp_html = Path(temp_dir) / f"test-report-{short_hash}.html"

    try:
        typer.echo("Downloading test-report.html artifact...")
        result = subprocess.run(
            [
                "gh",
                "run",
                "download",
                str(run_id),
                "--name",
                "test-report.html",
                "--dir",
                temp_dir,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            typer.secho(
                f"Failed to download artifact: {result.stderr}",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)

        # Find the downloaded HTML file (gh downloads into artifact name folder)
        downloaded = Path(temp_dir) / "test-report.html"
        if not downloaded.exists():
            # Check for file directly in temp_dir
            for p in Path(temp_dir).rglob("*.html"):
                downloaded = p
                break

        if not downloaded.exists():
            typer.secho(
                "test-report.html not found in downloaded artifact",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)

        # Rename to include commit hash for clarity
        downloaded.rename(temp_html)

    except subprocess.TimeoutExpired:
        typer.secho("Download timed out", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Open in browser
    file_url = f"file://{temp_html}"
    typer.echo(f"Opening report in browser: {temp_html}")
    webbrowser.open(file_url)

    typer.secho(
        f"\n✓ Test report for {short_hash} opened in browser",
        fg=typer.colors.GREEN,
    )
    typer.echo(f"  File saved at: {temp_html}")


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
    test_paths: list[Path] = typer.Option(
        [Path("test"), Path("src")], "-p", help="Test paths"
    ),
    view: str | None = typer.Option(
        None,
        "--view",
        help="View test report from GitHub for a commit hash (e.g. 7c0ed116 or HEAD~3)",
    ),
    open_browser: bool = typer.Option(
        False,
        "--open",
        help="Automatically open the live test report in your browser",
    ),
):
    import sys

    from faebryk.libs.util import repo_root

    # Handle --view option: fetch and open report, then exit
    if view is not None:
        # Support HEAD~N syntax
        commit_ref = view
        if view.startswith("HEAD~") or view == "HEAD":
            try:
                result = subprocess.run(
                    ["git", "rev-parse", view],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    commit_ref = result.stdout.strip()
            except Exception:
                pass  # Use as-is if git fails

        _fetch_and_open_test_report(commit_ref)
        return

    sys.path.insert(0, str(repo_root()))

    if direct:
        from test.runtest import logger as runtest_logger
        from test.runtest import run

        runtest_logger.setLevel(logging.INFO)

        if not test_name:
            raise ValueError("Test name is required when running directly")

        run(test_name=test_name, filepaths=test_paths)
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

    main(args=args, baseline_commit=baseline_commit, open_browser=open_browser)


@dev_app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def profile(
    ctx: typer.Context,
):
    import sys

    from faebryk.libs.util import repo_root

    sys.path.insert(0, str(repo_root()))
    from tools.profile import app

    sys.argv = ["", *ctx.args]
    app()
