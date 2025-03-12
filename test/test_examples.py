import os
import shutil
import sys
from pathlib import Path

import pytest

from faebryk.libs.util import repo_root as _repo_root
from faebryk.libs.util import run_live

# Get the examples directory relative to this test file
EXAMPLES_DIR = _repo_root() / "examples"

FABLL_EXAMPLES = [p for p in EXAMPLES_DIR.glob("*.py") if p.is_file()]
ATO_EXAMPLES = [p for p in EXAMPLES_DIR.glob("*.ato") if p.is_file()]

XFAILURES = {}


@pytest.mark.slow
@pytest.mark.parametrize(
    "example",
    (
        pytest.param(example, marks=pytest.mark.xfail(reason=reason))
        if (reason := XFAILURES.get(example.stem))
        else example
        for example in FABLL_EXAMPLES + ATO_EXAMPLES
    ),
    ids=lambda p: p.stem,
)
def test_examples_build(
    example: Path, tmp_path: Path, repo_root: Path, save_tmp_path_on_failure: None
):
    assert example.exists()

    example_copy = tmp_path / example.name
    example_copy.write_text(example.read_text())
    example = example_copy

    # Copy dependencies to the tmp dir directly because standalone mode doens't include
    example_modules = repo_root / "test" / "common" / "resources" / ".ato" / "modules"
    for item in example_modules.glob("*"):
        if item.is_dir():
            shutil.copytree(item, tmp_path / item.name)
        else:
            shutil.copy(item, tmp_path / item.name)

    _, stderr, _ = run_live(
        [
            sys.executable,
            "-m",
            "atopile",
            "build",
            "--standalone",
            f"{example}:App",
        ],
        env={**os.environ, "NONINTERACTIVE": "1"},
        cwd=tmp_path,
        stdout=print,
        stderr=print,
    )

    # TODO: add a strict mode to the CLI
    assert "Build successful! 🚀" in stderr
    assert stderr.count("✓") >= 1
    assert stderr.count("✗") == 0
    assert stderr.count("⚠") == 0


def test_example_project_builds(tmp_path: Path):
    example_proj = Path("examples")
    example_copy = tmp_path / "example_project"
    shutil.copytree(example_proj, example_copy)

    _, stderr, _ = run_live(
        [sys.executable, "-m", "atopile", "build"],
        cwd=example_copy,
        stdout=print,
        stderr=print,
    )

    assert "Build successful! 🚀" in stderr
    assert stderr.count("✓") >= 1
    assert stderr.count("✗") == 0
    assert stderr.count("⚠") == 0
