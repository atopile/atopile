import os
import sys
from pathlib import Path
from subprocess import run

import pytest

repo_root = Path.cwd()
while not (repo_root / "pyproject.toml").exists():
    repo_root = repo_root.parent


EXAMPLES_DIR = repo_root / "examples"

# TODO: remove these as they pass
XFAIL = [
    "iterative_design_nand",
    "mcu",
    "signal_processing",
]


@pytest.mark.slow
@pytest.mark.parametrize(
    "example",
    [
        pytest.param(
            p,
            marks=[pytest.mark.xfail(reason="Example stability is being improved")]
            if p.stem in XFAIL
            else [],
        )
        for p in EXAMPLES_DIR.glob("*.py")
    ],
    ids=lambda p: p.stem,
)
def test_example(example: Path):
    assert example.exists()

    result = run(
        [sys.executable, example],
        capture_output=True,
        text=True,
        env={**os.environ, "ATO_NON_INTERACTIVE": "1"},
    )
    assert result.returncode == 0
