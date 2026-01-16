import os
import sys

from faebryk.libs.util import run_live


def test_dev_flags_runs_and_prints_table_title():
    stdout, stderr, _ = run_live(
        [sys.executable, "-m", "atopile", "dev", "flags"],
        env={**os.environ, "NONINTERACTIVE": "1"},
        stdout=None,
        stderr=None,
    )

    # Rich renders to stdout; ensure we got a table header/title.
    assert "ConfigFlags" in stdout or "ConfigFlags" in stderr

