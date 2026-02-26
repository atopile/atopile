import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import webbrowser
from collections import Counter
from pathlib import Path

import typer

from atopile.logging import get_logger
from atopile.telemetry import capture

logger = get_logger(__name__)

dev_app = typer.Typer(rich_markup_mode="rich")


def _spawn_shell_with_venv(worktree_path: Path) -> None:
    """Start an interactive shell in worktree_path with .venv activated."""
    shell = os.environ.get("SHELL")
    if not shell:
        raise ValueError("SHELL is not set")

    venv_path = worktree_path / ".venv"
    venv_bin = venv_path / "bin"

    activate = venv_bin / "activate"
    if not activate.is_file():
        raise ValueError(f"activate script not found: {activate}")

    cmd = f". {shlex.quote(str(activate))} && exec {shlex.quote(shell)} -i"
    subprocess.run([shell, "-i", "-c", cmd], cwd=worktree_path, check=False)


@dev_app.command()
@capture("cli:dev_compile_start", "cli:dev_compile_end")
def compile():
    """Compile Zig native extensions."""
    print("compiling zig")
    # import will trigger compilation
    import faebryk.core.zig

    _ = faebryk.core.zig


@dev_app.command()
@capture("cli:dev_extension_start", "cli:dev_extension_end")
def extension(
    no_install: bool = typer.Option(
        False, "--no-install", help="Skip bun install step"
    ),
):
    """Launch VS Code Extension Development Host with webview watcher.

    Starts esbuild watch + bun build watch, then opens a new VS Code
    window in Extension Development Host mode loading the atopile extension.
    """
    from faebryk.libs.util import repo_root

    root = repo_root()
    ext_dir = root / "src" / "vscode-atopile"
    webview_dir = root / "src" / "ui" / "webview"

    # Validate directories exist
    if not ext_dir.is_dir():
        raise typer.BadParameter(f"Extension directory not found: {ext_dir}")

    # Check bun is available (also check ~/.bun/bin for fresh installs)
    bun = shutil.which("bun")
    if not bun:
        home_bun = Path.home() / ".bun" / "bin" / "bun"
        if home_bun.is_file():
            bun = str(home_bun)
        else:
            typer.secho(
                "bun not found. Install with: curl -fsSL https://bun.sh/install | bash",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)

    # Check code CLI is available
    code_bin = shutil.which("code")
    if not code_bin:
        typer.secho(
            "VS Code 'code' CLI not found. Install from VS Code command palette: "
            "'Shell Command: Install code command in PATH'",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    # Install dependencies
    if not no_install:
        typer.echo("Installing extension dependencies...")
        subprocess.run([bun, "install"], cwd=ext_dir, check=True)
        typer.echo("Installing webview dependencies...")
        subprocess.run([bun, "install"], cwd=webview_dir, check=True)

    # Build extension + hub + webview so there are dist/ files to load
    typer.echo("Building extension...")
    subprocess.run([bun, "run", "build:extension"], cwd=ext_dir, check=True)
    typer.echo("Building hub...")
    subprocess.run([bun, "run", "build:hub"], cwd=ext_dir, check=True)
    typer.echo("Building webview...")
    subprocess.run([bun, "run", "build:webview"], cwd=ext_dir, check=True)

    procs: list[subprocess.Popen] = []

    def cleanup(_signum=None, _frame=None):
        for p in procs:
            try:
                p.terminate()
            except OSError:
                pass
        for p in procs:
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()

    signal.signal(signal.SIGTERM, cleanup)

    try:
        # Start esbuild watch (rebuilds dist/extension.js on changes)
        typer.echo("Starting extension watcher...")
        procs.append(subprocess.Popen([bun, "run", "watch:extension"], cwd=ext_dir))

        # Start hub watcher (rebuilds hub-dist/main.js on changes)
        typer.echo("Starting hub watcher...")
        procs.append(subprocess.Popen([bun, "run", "watch:hub"], cwd=ext_dir))

        # Start bun build watch (rebuilds webview-ui/dist on changes)
        typer.echo("Starting webview watcher...")
        procs.append(subprocess.Popen([bun, "run", "watch:webview"], cwd=ext_dir))

        # Give watchers a moment to produce initial output
        time.sleep(2)

        # Launch VS Code Extension Development Host
        typer.echo("Launching VS Code Extension Development Host...")
        subprocess.Popen(
            [code_bin, "--extensionDevelopmentPath", str(ext_dir), str(root)],
        )

        typer.echo(
            "\nDev environment running:\n"
            "  - esbuild watch  (extension host)\n"
            "  - bun watch      (webview-ui)\n"
            "\nPress Ctrl+C to stop all watchers."
        )

        # Block until a watcher exits or user interrupts
        while True:
            for p in procs:
                if p.poll() is not None:
                    raise typer.Exit(p.returncode or 0)
            time.sleep(0.5)

    except KeyboardInterrupt:
        typer.echo("\nShutting down...")
    finally:
        cleanup()


@dev_app.command()
@capture("cli:dev_worktree_start", "cli:dev_worktree_end")
def worktree(
    name_suffix: str = typer.Argument(
        ...,
        help="Worktree name suffix. Defaults to <repo>_<suffix> for the path.",
    ),
    branch_name: str | None = typer.Option(
        None,
        "--branch",
        "-b",
        help="Branch to use. Defaults to the suffix. "
        "If it exists on origin, a local tracking branch is created.",
    ),
    path: Path | None = typer.Option(
        None,
        "--path",
        help="Explicit worktree path. Defaults to <parent>/<repo>_<suffix>.",
    ),
    start_point: str = typer.Option(
        "HEAD",
        "--start-point",
        help="Git ref to branch from when creating a new branch.",
    ),
    base_dir: Path | None = typer.Option(
        None,
        "--base-dir",
        help="Base directory used when --path is not provided.",
    ),
    source_root: Path | None = typer.Option(
        None,
        "--source-root",
        help="Main worktree to clone caches/venv from (auto-detected by default).",
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing cloned cache targets if needed."
    ),
    skip_editable_install: bool = typer.Option(
        False,
        "--skip-editable-install",
        help="Skip editable install step in the cloned worktree venv.",
    ),
    cd: bool = typer.Option(
        True,
        "--cd/--no-cd",
        help="Enter a shell in the new worktree after creation.",
    ),
):
    """
    Create a fast development worktree with cloned `.venv` and Zig artifacts.
    """
    from atopile.worktree import create_worktree

    try:
        worktree_path = create_worktree(
            name_suffix,
            branch_name=branch_name,
            path=path,
            start_point=start_point,
            base_dir=base_dir,
            source_root=source_root,
            force=force,
            skip_editable_install=skip_editable_install,
        )
    except (RuntimeError, FileExistsError, FileNotFoundError) as e:
        raise typer.BadParameter(str(e))

    if not cd:
        return

    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        typer.echo(
            f"Skipping shell handoff (non-interactive). "
            f"Use: cd {worktree_path} && source .venv/bin/activate"
        )
        return

    typer.echo(
        f"\nStarting a shell in {worktree_path} with .venv activated. "
        "Exit that shell to return here."
    )
    try:
        _spawn_shell_with_venv(worktree_path)
    except Exception as e:
        typer.secho(
            f"Error spawning shell: {e}. "
            f"Use: cd {worktree_path} && source .venv/bin/activate",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)


def _env_truthy(name: str) -> bool | None:
    val = os.getenv(name)
    if val is None:
        return None
    val_norm = val.strip().lower()
    if val_norm in {"0", "false", "no", "off"}:
        return False
    return True


def _count_callsites(
    flags: list,
    *,
    roots: list[Path],
) -> dict[tuple[Path, int, str], int]:
    """
    Best-effort "callsites" count for each flag.

    Implementation:
    - tokenize all `.py` files under roots
    - count NAME tokens matching each flag's python_name
    - subtract occurrences on the definition line (so the assignment isn't counted
      as a use)
    """
    import io
    import tokenize

    from atopile.config_flags import _iter_python_files

    tracked_names = {
        f.python_name for f in flags if f.python_name and f.python_name.isidentifier()
    }
    if not tracked_names:
        return {}

    exclusions = {
        (f.file.resolve(), f.line, f.python_name)
        for f in flags
        if f.python_name and f.python_name.isidentifier()
    }

    total: Counter[str] = Counter()
    excluded: Counter[tuple[Path, int, str]] = Counter()

    for path in _iter_python_files(*roots):
        p = path.resolve()
        try:
            src = path.read_text(encoding="utf-8")
        except Exception:
            continue

        try:
            tokens = tokenize.generate_tokens(io.StringIO(src).readline)
        except Exception:
            continue

        for tok in tokens:
            if tok.type != tokenize.NAME:
                continue
            if tok.string not in tracked_names:
                continue
            total[tok.string] += 1
            key = (p, tok.start[0], tok.string)
            if key in exclusions:
                excluded[key] += 1

    uses_by_def: dict[tuple[Path, int, str], int] = {}
    for f in flags:
        if not f.python_name or not f.python_name.isidentifier():
            continue
        key = (f.file.resolve(), f.line, f.python_name)
        uses = total[f.python_name] - excluded.get(key, 0)
        uses_by_def[key] = max(0, uses)

    return uses_by_def


@dev_app.command()
def flags():
    """
    Discover ConfigFlags in `src/atopile` and `src/faebryk` and print a rich table.

    This is intentionally best-effort and repo-local:
    - discovery is AST-based (no imports, no side effects)
    - callsite counts are token-based (no external tools)
    """
    import re

    from rich.table import Table

    from atopile.config_flags import discover_configflags
    from atopile.logging_utils import console

    def _linkify_urls(text: str) -> str:
        """Convert URLs to Rich hyperlinks with shorter display text."""
        url_pattern = r"(https?://[^\s]+)"

        def replace_url(match: re.Match) -> str:
            url = match.group(1)
            return f"[link={url}]{'link'}[/link]"

        return re.sub(url_pattern, replace_url, text)

    roots = [Path("src/atopile"), Path("src/faebryk")]
    here = Path.cwd()
    if not all((here / p).is_dir() for p in roots):
        raise FileNotFoundError(
            f"This command must be run from the '/atopile' folder, not from [{here}]."
        )
    roots = [here / p for p in roots]
    discovered = discover_configflags(*roots)
    uses_by_def = _count_callsites(discovered, roots=roots)

    table = Table(title="ConfigFlags", show_lines=True)
    table.add_column("Env", style="bold", no_wrap=True)
    table.add_column("Type", overflow="fold")
    table.add_column("Py Name", overflow="fold")
    table.add_column("Default", overflow="fold")
    table.add_column("Current", style="cyan", overflow="fold")
    table.add_column("Descr", overflow="fold", max_width=20)
    table.add_column("Location", style="dim", overflow="fold")
    table.add_column("Uses", justify="right", overflow="fold")

    for f in discovered:
        loc = f"{f.file}:{f.line}"
        uses = ""
        if f.python_name and f.python_name.isidentifier():
            uses = str(uses_by_def.get((f.file.resolve(), f.line, f.python_name), 0))

        # Convert URLs to clickable hyperlinks
        descr = _linkify_urls(f.descr) if f.descr else ""

        table.add_row(
            f.full_env_name,
            f.kind,
            f.python_name or "",
            f.default or "",
            f.current_value,
            descr,
            loc,
            uses,
        )

    console.print(table)


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
    save_baseline: str = typer.Option(
        None,
        "--save-baseline",
        "-s",
        help="Save results as a named local baseline (e.g. 'pre-refactor')",
    ),
    local_baseline: str = typer.Option(
        None,
        "--local-baseline",
        "-l",
        help="Compare against a local baseline by name",
    ),
    list_baselines: bool = typer.Option(
        False,
        "--list-baselines",
        help="List available local baselines and exit",
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
    reuse: bool = typer.Option(
        False,
        "--reuse",
        help="Reuse artifacts/test-report.json and rebuild with a new baseline without "
        "rerunning tests",
    ),
    keep_open: bool = typer.Option(
        False,
        "--keep-open",
        "-o",
        help="Keep the live report server running after tests finish",
    ),
):
    import sys

    from faebryk.libs.util import repo_root

    # Handle --list-baselines option: list and exit
    if list_baselines:
        sys.path.insert(0, str(repo_root()))
        from test.runner.baselines import list_local_baselines

        baselines = list_local_baselines()
        if not baselines:
            typer.echo("No local baselines found.")
        else:
            typer.echo("Available local baselines:")
            for b in baselines:
                typer.echo(
                    f"  {b['name']:<20} "
                    f"({b.get('tests_total', '?')} tests, "
                    f"created {b.get('created_at', 'unknown')})"
                )
        return

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

    # Convert number to HEAD~N format (e.g. "3" -> "HEAD~3")
    baseline_commit = baseline
    if baseline is not None:
        try:
            n = int(baseline)
            if n > 0:
                baseline_commit = f"HEAD~{n}"
        except ValueError:
            pass
        if baseline_commit and (
            baseline_commit == "HEAD" or baseline_commit.startswith("HEAD~")
        ):
            try:
                result = subprocess.run(
                    ["git", "rev-parse", baseline_commit],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    baseline_commit = result.stdout.strip()
            except Exception:
                pass

    if reuse:
        if direct:
            raise ValueError("--reuse cannot be combined with --direct")
        from test.runner.report import rebuild_reports_from_existing

        rebuild_reports_from_existing(
            report_path=Path("artifacts/test-report.json"),
            baseline_commit=baseline_commit,
        )
        if keep_open:
            from test.runner.main import run_report_server

            run_report_server(open_browser=open_browser)
        return

    if direct:
        import logging

        from test.runtest import TestNotFound, run
        from test.runtest import logger as runtest_logger

        runtest_logger.setLevel(logging.INFO)

        if not test_name:
            raise ValueError("Test name is required when running directly")

        try:
            run(test_name=test_name, filepaths=test_paths)
        except TestNotFound as e:
            print(e)
        return

    from test.runner.main import main

    args = ctx.args

    if ci:
        if "-m" in args:
            raise NotImplementedError("CI mode does not support -m")
        args.extend(["-m", "not not_in_ci and not regression and not slow"])
    if test_name:
        args.extend(["-k", test_name])

    main(
        args=args,
        baseline_commit=baseline_commit,
        local_baseline_name=local_baseline,
        save_baseline_name=save_baseline,
        open_browser=open_browser,
        keep_open=keep_open,
    )


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


@dev_app.command()
def clear_logs(
    ctx: typer.Context,
):
    """Remove all log databases."""
    from faebryk.libs.paths import remove_log_dir

    if remove_log_dir():
        typer.echo("🧹 Log databases removed 🧹")
    else:
        typer.echo("❌ Could not remove log databases")
