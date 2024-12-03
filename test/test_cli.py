import os
import sys
from subprocess import run

import pytest


@pytest.mark.parametrize("config", ["ato", "faebryk"])
def test_app(config):
    result = run(
        [sys.executable, "-m", "atopile", "build", "examples/project", "-b", config],
        capture_output=True,
        text=True,
        env={**os.environ, "ATO_NON_INTERACTIVE": "1"},
    )
    assert result.returncode == 0
    assert "Build successful!" in result.stdout
    assert "ERROR" not in result.stdout
