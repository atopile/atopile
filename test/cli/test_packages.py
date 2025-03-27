import os
import shutil
import sys
from pathlib import Path

import pytest

from faebryk.libs.util import repo_root as _repo_root
from faebryk.libs.util import run_live

# Get the examples directory relative to this test file
EXAMPLES_DIR = _repo_root() / "examples"


@pytest.mark.parametrize("package", ["xt-connectors"])
def test_install_package(package: str, tmp_path: Path):
    example_copy = tmp_path / "example"

    shutil.copytree(
        EXAMPLES_DIR,
        example_copy,
        ignore=lambda src, names: [".ato", "build", "standalone"],
    )

    _, stderr, _ = run_live(
        [sys.executable, "-m", "atopile", "install", package],
        env={**os.environ, "NONINTERACTIVE": "1"},
        cwd=example_copy,
        stdout=print,
        stderr=print,
    )

    assert f"Installing {package} in" in stderr
    assert "Done!" in stderr.splitlines()[-1]
