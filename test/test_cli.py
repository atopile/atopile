import logging
import os
import sys
from subprocess import run

import pytest

from faebryk.libs.util import run_live


# FIXME: this is because we're defaulting to the JLCPCB picker,
# which we don't have access to in the CI
@pytest.mark.not_in_ci
@pytest.mark.parametrize("config", ["ato", "fab"])
def test_app(config, caplog: pytest.LogCaptureFixture):
    caplog.set_level(logging.INFO)
    stdout, _ = run_live(
        [sys.executable, "-m", "atopile", "build", "examples/project", "-b", config],
        env={**os.environ, "ATO_NON_INTERACTIVE": "1"},
        stdout_level=logging.INFO,
    )
    assert "Build successful!" in stdout
    assert "ERROR" not in stdout


@pytest.mark.xfail(reason="Absolute performance will vary w/ hardware")
@pytest.mark.benchmark(
    min_rounds=10,
    max_time=0.3,
)
def test_snapiness(benchmark):
    def run_cli():
        return run(
            [sys.executable, "-m", "atopile", "--help"],
            capture_output=True,
            text=True,
            env={**os.environ, "ATO_NON_INTERACTIVE": "1"},
        )

    result = benchmark(run_cli)
    assert result.returncode == 0
