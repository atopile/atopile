import logging
import os
import sys
from pathlib import Path

import pytest

from faebryk.libs.util import run_live

repo_root = Path.cwd()
while not (repo_root / "pyproject.toml").exists():
    repo_root = repo_root.parent


EXAMPLES_DIR = repo_root / "examples"

# TODO: remove these as they pass
XFAIL = [
    "ch2_8_iterative_design_nand",
    "ch2_4_signal_processing",
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
def test_example(example: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.INFO)
    assert example.exists()

    example_copy = tmp_path / example.name
    example_copy.write_text(example.read_text())
    example = example_copy

    run_live(
        [sys.executable, "-m", "atopile", "build", "--standalone", f"{example}:App"],
        env={**os.environ, "ATO_NON_INTERACTIVE": "1"},
        cwd=tmp_path,
        stdout_level=logging.INFO,
    )


@pytest.mark.parametrize("example", XFAIL)
def test_xfail_list_exists(example: str):
    assert (EXAMPLES_DIR / f"{example}.py").exists(), "Handle the missing xfail example"
