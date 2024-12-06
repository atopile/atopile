import os
import sys
from subprocess import run

import pytest


# FIXME: this is because we're defaulting to the JLCPCB picker,
# which we don't have access to in the CI
@pytest.mark.not_in_ci
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
