import json
import logging
import subprocess
import tempfile
import webbrowser
from collections import Counter
from dataclasses import dataclass
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


@dataclass(frozen=True)
class _ConfigFlagDef:
    env_name: str
    kind: str
    python_name: str | None
    file: Path
    line: int
    default: str | None
    descr: str | None


def _iter_python_files(*roots: Path) -> list[Path]:
    out: list[Path] = []
    for r in roots:
        if not r.exists():
            continue
        out.extend(p for p in r.rglob("*.py") if p.is_file())
    return out


def _format_ast_target(target) -> str | None:
    import ast

    match target:
        case ast.Name(id=name):
            return name
        case ast.Attribute(value=base, attr=attr):
            base_s = _format_ast_target(base)
            if base_s is None:
                return attr
            return f"{base_s}.{attr}"
        case _:
            return None


def _extract_str_constant(node) -> str | None:
    import ast

    match node:
        case ast.Constant(value=str_val) if isinstance(str_val, str):
            return str_val
        case _:
            return None


def _extract_literal_repr(node) -> str | None:
    import ast

    match node:
        case ast.Constant(value=v):
            return repr(v)
        case ast.Name(id=name):
            # best-effort: many defaults are literals; if not, still provide identifier
            return name
        case ast.UnaryOp(op=ast.USub(), operand=ast.Constant(value=v)) if isinstance(
            v, (int, float)
        ):
            return repr(-v)
        case _:
            return None


def _is_configflag_ctor(call) -> str | None:
    """
    Return the constructor name if `call` looks like ConfigFlag*(...) or None.
    """
    import ast

    if not isinstance(call, ast.Call):
        return None

    fn = call.func
    name = None
    if isinstance(fn, ast.Name):
        name = fn.id
    elif isinstance(fn, ast.Attribute):
        name = fn.attr

    if name in {"ConfigFlag", "ConfigFlagInt", "ConfigFlagFloat", "ConfigFlagString"}:
        return name
    return None


def _find_configflags_in_assignment(value, *, file: Path, line: int, python_name: str):
    import ast

    found: list[_ConfigFlagDef] = []
    for node in ast.walk(value):
        if not isinstance(node, ast.Call):
            continue
        ctor = _is_configflag_ctor(node)
        if ctor is None:
            continue

        env_name = _extract_str_constant(node.args[0]) if node.args else None
        if not env_name:
            continue

        default: str | None = None
        descr: str | None = None
        for kw in node.keywords:
            if kw.arg == "default":
                default = _extract_literal_repr(kw.value)
            elif kw.arg == "descr":
                descr = _extract_str_constant(kw.value) or _extract_literal_repr(
                    kw.value
                )

        # Common positional patterns used in this repo:
        # - ConfigFlag("NAME", False, "descr")
        # - ConfigFlag("NAME", False)
        if default is None and len(node.args) >= 2:
            default = _extract_literal_repr(node.args[1])
        if descr is None and len(node.args) >= 3:
            descr = _extract_str_constant(node.args[2]) or _extract_literal_repr(
                node.args[2]
            )

        found.append(
            _ConfigFlagDef(
                env_name=env_name,
                kind=ctor,
                python_name=python_name,
                file=file,
                line=line,
                default=default,
                descr=descr,
            )
        )

    return found


def _discover_configflags(*roots: Path) -> list[_ConfigFlagDef]:
    import ast

    flags: list[_ConfigFlagDef] = []
    for path in _iter_python_files(*roots):
        try:
            src = path.read_text(encoding="utf-8")
        except Exception:
            continue
        try:
            tree = ast.parse(src, filename=str(path))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if not node.targets:
                    continue
                python_name = _format_ast_target(node.targets[0])
                if python_name is None:
                    continue
                flags.extend(
                    _find_configflags_in_assignment(
                        node.value,
                        file=path,
                        line=node.lineno,
                        python_name=python_name,
                    )
                )
            elif isinstance(node, ast.AnnAssign):
                python_name = _format_ast_target(node.target)
                if python_name is None or node.value is None:
                    continue
                flags.extend(
                    _find_configflags_in_assignment(
                        node.value,
                        file=path,
                        line=node.lineno,
                        python_name=python_name,
                    )
                )

    # Dedupe exact duplicates (same env/type/location/name)
    uniq: dict[tuple[str, str, str, int, str | None], _ConfigFlagDef] = {}
    for f in flags:
        k = (f.env_name, f.kind, str(f.file), f.line, f.python_name)
        uniq[k] = f
    return sorted(
        uniq.values(), key=lambda f: (f.env_name, f.kind, str(f.file), f.line)
    )


def _count_callsites(
    flags: list[_ConfigFlagDef],
    *,
    roots: list[Path],
) -> dict[tuple[Path, int, str], int]:
    """
    Best-effort "callsites" count for each flag.

    Implementation:
    - tokenize all `.py` files under roots
    - count NAME tokens matching each flag's python_name
    - subtract occurrences on the definition line (so the assignment isn't counted as a use)
    """
    import io
    import tokenize

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
    from rich.console import Console
    from rich.table import Table

    roots = [Path("src/atopile"), Path("src/faebryk")]
    discovered = _discover_configflags(*roots)
    uses_by_def = _count_callsites(discovered, roots=roots)

    table = Table(title="ConfigFlags", show_lines=True)
    table.add_column("Env", style="bold")
    table.add_column("Type")
    table.add_column("Py Name")
    table.add_column("Default")
    table.add_column("Descr", overflow="fold")
    table.add_column("Location", style="dim")
    table.add_column("Uses", justify="right")

    for f in discovered:
        loc = f"{f.file}:{f.line}"
        uses = ""
        if f.python_name and f.python_name.isidentifier():
            uses = str(uses_by_def.get((f.file.resolve(), f.line, f.python_name), 0))

        table.add_row(
            f.env_name,
            f.kind,
            f.python_name or "",
            f.default or "",
            f.descr or "",
            loc,
            uses,
        )

    Console().print(table)


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
