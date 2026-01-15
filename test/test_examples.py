import os
import shutil
import sys
from pathlib import Path

import pytest

from faebryk.libs.util import repo_root as _repo_root
from faebryk.libs.util import run_live

# Get the examples directory relative to this test file
EXAMPLES_DIR = _repo_root() / "examples"

SLOW_EXAMPLES = [
    "led_badge",
]


@pytest.mark.parametrize(
    "example",
    [
        pytest.param(manifest.parent)
        for manifest in EXAMPLES_DIR.glob("*/ato.yaml")
        if manifest.parent.stem not in SLOW_EXAMPLES
    ],
    ids=lambda p: p.stem,
)
def test_examples_build_fast(
    example: Path, tmp_path: Path, repo_root: Path, save_tmp_path_on_failure: None
):
    example_copy = tmp_path / example.name
    shutil.copytree(example, example_copy)

    assert example_copy.exists()

    stdout, stderr, _ = run_live(
        [sys.executable, "-m", "atopile", "build", "-v"],
        env={**os.environ, "NONINTERACTIVE": "1"},
        cwd=example_copy,
        stdout=print,
        stderr=print,
        timeout=180,
    )

    # TODO: add a strict mode to the CLI

    combined = stdout + stderr
    print(stderr)

    assert "Build successful! 🚀" in combined
    assert combined.count("✓") >= 1
    assert combined.count("✗") == 0

    # expected warnings:
    # - missing kicad-cli for '3d-model' target (in CI only)
    # - container modules without footprints (e.g. layout_reuse)
    # - cache updates for KiCAD file format changes
    assert combined.count("⚠") <= 3


@pytest.mark.slow
@pytest.mark.parametrize(
    "example",
    [
        pytest.param(manifest.parent)
        for manifest in EXAMPLES_DIR.glob("*/ato.yaml")
        if manifest.parent.stem in SLOW_EXAMPLES
    ],
    ids=lambda p: p.stem,
)
def test_examples_build_slow(
    example: Path, tmp_path: Path, repo_root: Path, save_tmp_path_on_failure: None
):
    example_copy = tmp_path / example.name
    shutil.copytree(example, example_copy)

    assert example_copy.exists()

    stdout, stderr, _ = run_live(
        [sys.executable, "-m", "atopile", "build"],
        env={**os.environ, "NONINTERACTIVE": "1"},
        cwd=example_copy,
        stdout=print,
        stderr=print,
    )

    # TODO: add a strict mode to the CLI
    combined = stdout + stderr
    assert "Build successful! 🚀" in combined
    assert combined.count("✓") >= 1
    assert combined.count("✗") == 0

    # expected warnings:
    # - missing kicad-cli for '3d-model' target (in CI only)
    # - container modules without footprints (e.g. layout_reuse)
    # - cache updates for KiCAD file format changes
    assert combined.count("⚠") <= 3
