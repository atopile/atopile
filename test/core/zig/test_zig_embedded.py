import itertools
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Generator
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


def file_contains_pattern(path: Path, pattern: re.Pattern | str) -> bool:
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
        cmd.extend(["--test-filter", test_filter])

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


def _escape_shell_args(args: list[str]) -> str:
    # TODO put more effort into this
    # TODO move to util.py
    def _escape_arg(arg: str) -> str:
        if " " in arg:
            return f"'{arg}'"
        return arg

    return " ".join([_escape_arg(arg) for arg in args])


def run_gdb(test_bin: Path) -> None:
    # TODO move to util.py

    core_file = test_bin.with_suffix(".core")
    subprocess.run(
        ["coredumpctl", "dump", test_bin, *["--output", core_file]],
        capture_output=True,
        check=True,
    )

    args = """-q -batch \
        -ex 'set debuginfod enabled off' \
        -ex 'thread apply all bt 20' \
        -ex 'echo ===BOTTOM===\n' \
        -ex 'thread apply all bt -20' \
        | awk '
        $0=="===BOTTOM===" {bottom=1; next}

        # top section: print as-is
        !bottom {print; next}

        # bottom section: only print per-thread blocks if they contain frames >= 20
        /^Thread [0-9]+/ {
            if (seen) { for (i=1;i<=n;i++) print buf[i] }
            delete buf; n=0; seen=0
            buf[++n]=$0
            next
        }

        # keep only frames #20+ (drop overlap/shallow)
        match($0, /^#([0-9]+)/, m) {
            if (m[1] >= 20) { buf[++n]=$0; seen=1 }
            next
        }

        # keep other lines (but only if we end up keeping some frames)
        { buf[++n]=$0 }
        END { if (seen) { for (i=1;i<=n;i++) print buf[i] } }
        '
    """
    cmd = f"gdb {test_bin} {core_file} {args}"
    print(f"Attach gdb with: `gdb {test_bin} {core_file}")
    subprocess.run(cmd, shell=True, capture_output=False, check=True)


@pytest.mark.parametrize("zig_test", discover_zig_tests(), ids=zig_test_id)
def test_zig_embedded(zig_test: tuple[Path, str]) -> None:
    """Run a single zig embedded test."""
    zig_file, test_name = zig_test
    cmd = build_zig_test_command(zig_file, test_filter=test_name)
    with tempfile.TemporaryDirectory(delete=False) as temp_dir:
        test_bin = Path(temp_dir) / "test"
        compile_cmd = [
            *cmd,
            "--test-no-exec",
            f"-femit-bin={test_bin}",
            "-fno-omit-frame-pointer",
            *["-O", "Debug"],
            "-fno-strip",
            "-fsanitize-c",
        ]
        compile_result = subprocess.run(
            compile_cmd,
            cwd=ZIG_SRC_DIR,
            capture_output=False,
        )
        if not compile_result.returncode == 0:
            print(f"Compile failed for {_escape_shell_args(cmd)}")
            assert False

        result = subprocess.run(
            [test_bin],
            capture_output=False,
        )

        if result.returncode != 0:
            try:
                # TODO we should do this will all tests when they crash
                run_gdb(test_bin)
            except subprocess.CalledProcessError:
                pass

        assert result.returncode == 0
        shutil.rmtree(temp_dir, ignore_errors=True)


def main(glob_pattern: str, test_name: str):
    paths = list(ZIG_SRC_DIR.rglob(glob_pattern))
    if not len(paths) == 1:
        raise ValueError(f"Expected 1 path, got {len(paths)}")
    path = paths[0]

    test_zig_embedded(
        (
            path,
            test_name,
        )
    )


if __name__ == "__main__":
    import typer

    from faebryk.libs.logging import setup_basic_logging

    setup_basic_logging()
    typer.run(main)
