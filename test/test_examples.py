import os
import sys
from pathlib import Path

import pytest

from faebryk.libs.util import repo_root as _repo_root
from faebryk.libs.util import run_live

repo_root = _repo_root()
EXAMPLES_DIR = repo_root / "examples"


@pytest.mark.slow
@pytest.mark.parametrize(
    "example",
    list(EXAMPLES_DIR.glob("*.py")),
    ids=lambda p: p.stem,
)
def test_fabll_example(example: Path, tmp_path: Path):
    assert example.exists()

    example_copy = tmp_path / example.name
    example_copy.write_text(example.read_text())
    example = example_copy

    run_live(
        [sys.executable, "-m", "atopile", "build", "--standalone", f"{example}:App"],
        env={**os.environ, "ATO_NON_INTERACTIVE": "1"},
        cwd=tmp_path,
        stdout=print,
        stderr=print,
    )
