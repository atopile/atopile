import os
import re
import shutil
import sys
from pathlib import Path

import pytest

from faebryk.libs.util import repo_root as _repo_root
from faebryk.libs.util import run_live


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


# Get the examples directory relative to this test file
EXAMPLES_DIR = _repo_root() / "examples"


@pytest.mark.parametrize("package", ["atopile/addressable-leds"])
def test_install_package(package: str, tmp_path: Path):
    example_copy = tmp_path / "example"

    shutil.copytree(
        EXAMPLES_DIR / "quickstart",
        example_copy,
        ignore=lambda src, names: [".ato", "build", "standalone"],
    )

    stdout, stderr, _ = run_live(
        [sys.executable, "-m", "atopile", "add", package],
        env={**os.environ, "NONINTERACTIVE": "1"},
        cwd=example_copy,
        stdout=print,
        stderr=print,
    )

    # Check combined output (FBRK_LOG_FMT affects which stream logs go to)
    # Strip ANSI codes since Rich renders markup like [green]+[/] to escape sequences
    combined = _strip_ansi(stdout + stderr)
    assert f"+ {package}@" in combined
    assert "Done!" in stdout.splitlines()[-1]
