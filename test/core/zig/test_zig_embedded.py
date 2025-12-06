import itertools
import re
import subprocess
from collections.abc import Generator
from pathlib import Path

import pytest

from faebryk.libs.util import repo_root

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
        cmd = ["zig", "test", str(rel_path)]
    else:
        cmd = [
            "zig",
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


def test_zig_embedded_tests(subtests: "pytest.Subtests") -> None:
    """Run zig test on all files containing embedded tests."""
    test_files = discover_zig_test_files()
    ran_a_test = False

    for zig_file in test_files:
        rel_path = zig_file.relative_to(ZIG_SRC_DIR)

        for test_name in TEST_NAME_PATTERN.findall(zig_file.read_text()):
            with subtests.test(msg=f"{rel_path}::{test_name}"):
                ran_a_test = True
                cmd = build_zig_test_command(zig_file, test_filter=test_name)
                result = subprocess.run(
                    cmd,
                    cwd=ZIG_SRC_DIR,
                    capture_output=True,
                    text=True,
                )
                assert result.returncode == 0, (
                    f"zig test failed for {rel_path}::{test_name}\n"
                    f"Command: {' '.join(cmd)}\n"
                    f"stderr:\n{result.stderr}"
                )

    assert ran_a_test, "No tests ran"
