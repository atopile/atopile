import itertools
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from faebryk.libs.util import repo_root

ZIG_COMMAND = [sys.executable, "-m", "ziglang"]

ZIG_SRC_DIR = repo_root() / "src" / "faebryk" / "core" / "zig"

# Module definitions: name -> (path, dependencies)
# Order matters: modules must be defined after their dependencies
ZIG_MODULES: dict[str, tuple[str, list[str]]] = {
    "graph": ("src/graph/lib.zig", []),
    "faebryk": ("src/faebryk/lib.zig", ["graph"]),
    "sexp": ("src/sexp/lib.zig", []),
}


TEST_NAME_PATTERN = re.compile(r'^test "([^"]+)"', re.MULTILINE)
TEST_BLOCK_PATTERN = re.compile(r'^test "')


def file_contains_pattern(path: Path, pattern: re.Pattern[str] | str) -> bool:
    with path.open() as f:
        for line in f:
            if re.search(pattern, line):
                return True
    return False


def discover_zig_test_files() -> Generator[Path, None, None]:
    """Find all .zig files containing test blocks under src/."""
    return (
        f
        for f in (ZIG_SRC_DIR / "src").rglob("*.zig")
        if file_contains_pattern(f, TEST_BLOCK_PATTERN)
    )


def build_zig_test_command(zig_file: Path, test_filter: str | None = None) -> list[str]:
    """Build the zig test command for a file."""
    rel_path = zig_file.relative_to(ZIG_SRC_DIR)

    imports = []
    for module_name in ZIG_MODULES:
        if file_contains_pattern(zig_file, rf'@import\("{module_name}"\)'):
            imports.append(module_name)

    if not imports:
        cmd = [*ZIG_COMMAND, "test", str(rel_path)]
    else:
        cmd = [
            *ZIG_COMMAND,
            "test",
            *itertools.chain.from_iterable(["--dep", dep] for dep in imports),
            f"-Mroot={rel_path}",
        ]

        for module_name in imports:
            module_path, module_deps = ZIG_MODULES[module_name]
            for dep in module_deps:
                cmd.extend(["--dep", dep])
            cmd.append(f"-M{module_name}={module_path}")

    if test_filter:
        cmd.extend(["--test-filter", f"{zig_file.stem}.test.{test_filter}"])

    return cmd


def discover_zig_tests() -> list[tuple[Path, str]]:
    """Discover all zig tests as (file, test_name) pairs."""
    tests = [
        (zig_file, test_name)
        for zig_file in discover_zig_test_files()
        for test_name in TEST_NAME_PATTERN.findall(zig_file.read_text())
    ]
    assert len(tests) > 0, "No zig tests found"
    return tests


def zig_test_id(param: tuple[Path, str]) -> str:
    zig_file, test_name = param
    rel_path = zig_file.relative_to(ZIG_SRC_DIR)
    return f"{rel_path}:{test_name}"


@dataclass
class ZigTestResult:
    """Result of a single zig test."""

    passed: bool | None  # True=OK, False=FAIL, None=SKIP
    output: str  # stderr lines for this test


@dataclass
class FileTestResults:
    """Cached results from running all tests in a zig file."""

    test_results: dict[str, ZigTestResult] = field(default_factory=dict)
    stdout: str = ""
    stderr: str = ""
    compile_error: str | None = None


# Per-process cache: zig file -> results from running all its tests
_zig_file_cache: dict[Path, FileTestResults] = {}

# Zig test output line: "N/M qualified.name...RESULT"
_ZIG_TEST_LINE = re.compile(r"^(\d+/\d+) (.+)\.\.\.")
_ZIG_RESULT_LINE = re.compile(r"^(OK|FAIL|SKIP)")


def _parse_zig_test_output(stderr: str) -> dict[str, ZigTestResult]:
    """Parse zig test runner non-TTY stderr output.

    Returns dict mapping test_name -> ZigTestResult.
    Test names have the module prefix stripped (everything up to '.test.').
    """
    results: dict[str, ZigTestResult] = {}
    current_name: str | None = None
    current_lines: list[str] = []

    def _finish(name: str, passed: bool | None) -> None:
        results[name] = ZigTestResult(passed=passed, output="\n".join(current_lines))

    for line in stderr.splitlines():
        m = _ZIG_TEST_LINE.match(line)
        if m:
            qualified_name = m.group(2)
            # Strip module prefix: "root.test.foo" -> "foo"
            dot_test = ".test."
            idx = qualified_name.find(dot_test)
            if idx >= 0:
                current_name = qualified_name[idx + len(dot_test) :]
            else:
                current_name = qualified_name
            current_lines = [line]

            # Check if result is on the same line (after "...")
            rest = line[m.end() :]
            if rest.startswith("OK"):
                _finish(current_name, True)
                current_name = None
            elif rest.startswith("FAIL"):
                _finish(current_name, False)
                current_name = None
            elif rest.startswith("SKIP"):
                _finish(current_name, None)
                current_name = None
            # else: test printed debug output, result on a subsequent line
        elif current_name is not None:
            current_lines.append(line)
            rm = _ZIG_RESULT_LINE.match(line)
            if rm:
                result_str = rm.group(1)
                if result_str == "OK":
                    _finish(current_name, True)
                elif result_str == "FAIL":
                    _finish(current_name, False)
                else:
                    _finish(current_name, None)
                current_name = None

    return results


def _run_all_zig_tests(
    zig_file: Path, release_mode: str = "ReleaseFast"
) -> FileTestResults:
    """Compile and run all tests in a zig file, returning parsed results."""
    test_bin, compile_result = compile_zig_test_binary(
        zig_file, test_filter=None, release_mode=release_mode
    )

    if compile_result.returncode != 0:
        stderr = compile_result.stderr.decode(errors="replace")
        return FileTestResults(
            stdout=compile_result.stdout.decode(errors="replace"),
            stderr=stderr,
            compile_error=stderr,
        )

    run_result = run_zig_binary(test_bin)
    stdout = run_result.stdout.decode(errors="replace")
    stderr = run_result.stderr.decode(errors="replace")

    shutil.rmtree(test_bin.parent, ignore_errors=True)

    test_results = _parse_zig_test_output(stderr)
    return FileTestResults(
        test_results=test_results,
        stdout=stdout,
        stderr=stderr,
    )


def _test_zig_embedded(
    zig_test: tuple[Path, str], release_mode: str = "ReleaseFast"
) -> None:
    """Run a single zig embedded test (using per-file cache)."""
    zig_file, test_name = zig_test

    cached = _zig_file_cache.get(zig_file)
    if cached is None:
        print(f"Cache miss: compiling + running all tests in {zig_file.name}")
        cached = _run_all_zig_tests(zig_file, release_mode)
        _zig_file_cache[zig_file] = cached
    else:
        print(f"Cache hit: {zig_file.name}")

    if cached.compile_error:
        print(cached.stderr)
        pytest.fail(f"Compile error for {zig_file.name}:\n{cached.compile_error}")

    if test_name not in cached.test_results:
        print(cached.stderr)
        pytest.fail(
            f"Test '{test_name}' not found in zig output for {zig_file.name}. "
            f"Known tests: {list(cached.test_results.keys())}"
        )

    test_result = cached.test_results[test_name]
    print(test_result.output)

    if test_result.passed is None:
        pytest.skip(f"Zig test '{test_name}' was skipped")

    if not test_result.passed:
        pytest.fail(f"Zig test '{test_name}' failed")


@pytest.mark.max_parallel(16)
@pytest.mark.worker_affinity(separator=":")
@pytest.mark.parametrize("zig_test", discover_zig_tests(), ids=zig_test_id)
def test_zig_embedded(zig_test: tuple[Path, str]):
    _test_zig_embedded(zig_test)


def compile_zig_test_binary(
    zig_file: Path,
    test_filter: str | None = None,
    release_mode: str = "ReleaseFast",
) -> tuple[Path, subprocess.CompletedProcess[bytes]]:
    """Compile a zig test binary without executing it. Returns (binary_path, result)."""
    cmd = build_zig_test_command(zig_file, test_filter=test_filter)
    temp_dir = tempfile.mkdtemp()
    test_bin = Path(temp_dir) / "test"
    compile_cmd = [
        *cmd,
        "--test-no-exec",
        f"-femit-bin={test_bin}",
        "-fno-omit-frame-pointer",
        "-O",
        release_mode,
        "-fno-strip",
        "-fsanitize-c",
        "-lc",
    ]
    result = subprocess.run(
        compile_cmd,
        cwd=ZIG_SRC_DIR,
        capture_output=True,
    )
    return test_bin, result


def run_zig_binary(
    test_bin: Path, args: list[str] | None = None
) -> subprocess.CompletedProcess[bytes]:
    """Run a compiled zig test binary."""
    cmd = [str(test_bin)]
    if args:
        cmd.extend(args)
    return subprocess.run(cmd, capture_output=True)


def main(glob_pattern: str, test_name: str) -> None:
    paths = list(ZIG_SRC_DIR.rglob(glob_pattern))
    if not len(paths) == 1:
        raise ValueError(f"Expected 1 path, got {len(paths)}")
    path = paths[0]

    _test_zig_embedded(
        (
            path,
            test_name,
        ),
        release_mode=os.getenv("FBRK_ZIG_RELEASEMODE", "ReleaseFast"),
    )


if __name__ == "__main__":
    import typer

    app = typer.Typer()
    app.command(name="run")(main)
    app()
