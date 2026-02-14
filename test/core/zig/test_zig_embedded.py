import os
import re
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path

import pytest

from faebryk.libs.util import debug_perf, repo_root

ZIG_COMMAND = [sys.executable, "-m", "ziglang"]

ZIG_SRC_DIR = repo_root() / "src" / "faebryk" / "core" / "zig"

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


def _test_binary_name(zig_file: Path) -> str:
    """Derive a unique binary name from the zig file path."""
    return f"{zig_file.parent.name}-{zig_file.stem}"


def _test_filter_name(zig_file: Path, test_name: str) -> str:
    """Build the qualified filter name: <stem>.test.<name>."""
    return f"{zig_file.stem}.test.{test_name}"


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


@debug_perf
def compile_zig_test_binary(
    zig_file: Path,
    release_mode: str = "ReleaseFast",
) -> tuple[Path, subprocess.CompletedProcess[bytes]]:
    """Compile a zig test binary via build.zig. Returns (binary_path, result)."""
    rel_path = str(zig_file.relative_to(ZIG_SRC_DIR))
    bin_name = _test_binary_name(zig_file)
    cmd = [
        *ZIG_COMMAND,
        "build",
        "test-file",
        f"-Dtest-file={rel_path}",
        f"-Dtest-name={bin_name}",
        f"-Doptimize={release_mode}",
    ]
    result = subprocess.run(cmd, cwd=ZIG_SRC_DIR, capture_output=True)
    test_bin = ZIG_SRC_DIR / "zig-out" / "bin" / bin_name
    return test_bin, result


def run_zig_binary(
    test_bin: Path, args: list[str] | None = None
) -> subprocess.CompletedProcess[bytes]:
    """Run a compiled zig test binary."""
    cmd = [str(test_bin)]
    if args:
        cmd.extend(args)
    return subprocess.run(cmd, capture_output=True)


# Per-process cache: skip zig build cache check for already-compiled files
_compiled: dict[Path, str | None] = {}  # zig_file -> compile_error or None


def _ensure_compiled(zig_file: Path, release_mode: str = "ReleaseFast") -> Path:
    """Compile once per file per process. Returns binary path."""
    if zig_file not in _compiled:
        test_bin, result = compile_zig_test_binary(zig_file, release_mode=release_mode)
        if result.returncode != 0:
            err = result.stderr.decode(errors="replace")
            _compiled[zig_file] = err
        else:
            _compiled[zig_file] = None

    err = _compiled[zig_file]
    if err is not None:
        print(err)
        pytest.fail(f"Compile error for {zig_file.name}:\n{err}")

    return ZIG_SRC_DIR / "zig-out" / "bin" / _test_binary_name(zig_file)


def _test_zig_embedded(
    zig_test: tuple[Path, str], release_mode: str = "ReleaseFast"
) -> None:
    """Compile (once per file) and run a single zig test."""
    zig_file, test_name = zig_test

    test_bin = _ensure_compiled(zig_file, release_mode)

    qualified = _test_filter_name(zig_file, test_name)
    run_result = run_zig_binary(test_bin, args=["--test-filter", qualified])
    stderr = run_result.stderr.decode(errors="replace")
    print(stderr)

    if run_result.returncode != 0:
        pytest.fail(f"Zig test '{test_name}' failed:\n{stderr}")


# @pytest.mark.max_parallel(16)
@pytest.mark.worker_affinity(separator=":")
@pytest.mark.parametrize("zig_test", discover_zig_tests(), ids=zig_test_id)
def test_zig_embedded(zig_test: tuple[Path, str]):
    _test_zig_embedded(zig_test)


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
