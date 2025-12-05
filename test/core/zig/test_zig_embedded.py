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


def file_contains_pattern(path: Path, pattern: re.Pattern) -> bool:
    with path.open() as f:
        for line in f:
            if pattern.search(line):
                return True
    return False


def discover_zig_test_files() -> Generator[Path, None, None]:
    """Find all .zig files containing test blocks under src/."""
    test_pattern = re.compile(r'^test "')
    return (
        f
        for f in (ZIG_SRC_DIR / "src").rglob("*.zig")
        if file_contains_pattern(f, test_pattern)
    )


def build_zig_test_command(zig_file: Path) -> list[str]:
    """Build the zig test command for a file."""
    rel_path = zig_file.relative_to(ZIG_SRC_DIR)

    imports = []
    for module_name in ZIG_MODULES:
        if file_contains_pattern(zig_file, re.compile(rf'@import\("{module_name}"\)')):
            imports.append(module_name)

    if not imports:
        return ["zig", "test", str(rel_path)]

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

    return cmd


def test_zig_embedded_tests(subtests: "pytest.Subtests") -> None:
    """Run zig test on all files containing embedded tests."""
    test_files = discover_zig_test_files()

    for zig_file in test_files:
        rel_path = zig_file.relative_to(ZIG_SRC_DIR)
        with subtests.test(msg=str(rel_path)):
            cmd = build_zig_test_command(zig_file)
            result = subprocess.run(
                cmd,
                cwd=ZIG_SRC_DIR,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, (
                f"zig test failed for {rel_path}\n"
                f"Command: {' '.join(cmd)}\n"
                f"stderr:\n{result.stderr}"
            )
