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

SLOW = {"ch2_8_mcu"}
XFAILURES = {"ch2_8_mcu": "Pin matching issues"}


def _get_marks(example: Path):
    return [
        *(
            [pytest.mark.xfail(reason=XFAILURES[example.stem])]
            if example.stem in XFAILURES
            else []
        ),
        *([pytest.mark.slow] if example.stem in SLOW else []),
    ]


@pytest.mark.parametrize(
    "example",
    [
        pytest.param(example, marks=_get_marks(example))
        for example in FABLL_EXAMPLES + ATO_EXAMPLES
    ],
    ids=lambda p: p.stem,
)
def test_examples_build(
    example: Path, tmp_path: Path, repo_root: Path, save_tmp_path_on_failure: None
):
    assert example.exists()

    example_copy = tmp_path / example.name
    example_copy.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
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
