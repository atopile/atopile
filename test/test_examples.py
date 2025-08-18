import os
import shutil
import sys
from pathlib import Path

import pytest

from faebryk.libs.util import repo_root as _repo_root
from faebryk.libs.util import run_live

# Get the examples directory relative to this test file
EXAMPLES_DIR = _repo_root() / "examples"


EXAMPLE_PARAMS = []
for manifest in EXAMPLES_DIR.glob("*/ato.yaml"):
    example_dir = manifest.parent
    # Increase timeout for slow examples
    if example_dir.name == "led_badge":
        EXAMPLE_PARAMS.append(pytest.param(example_dir, marks=pytest.mark.timeout(900)))
    else:
        EXAMPLE_PARAMS.append(pytest.param(example_dir))


@pytest.mark.parametrize(
    "example",
    EXAMPLE_PARAMS,
    ids=lambda p: p.stem,
)
def test_examples_build(
    example: Path, tmp_path: Path, repo_root: Path, save_tmp_path_on_failure: None
):
    example_copy = tmp_path / example.name
    shutil.copytree(example, example_copy)

    assert example_copy.exists()

    build_cmd = [sys.executable, "-m", "atopile", "build"]
    if example.name == "led_badge":
        build_cmd.append("--keep-picked-parts")

    _, stderr, _ = run_live(
        build_cmd,
        env={**os.environ, "NONINTERACTIVE": "1"},
        cwd=example_copy,
        stdout=print,
        stderr=print,
    )

    # TODO: add a strict mode to the CLI
    assert "Build successful! 🚀" in stderr
    assert stderr.count("✓") >= 1
    assert stderr.count("✗") == 0

    # expected warnings:
    # - missing kicad-cli for '3d-model' target (in CI only)
    assert stderr.count("⚠") in (0, 1)
