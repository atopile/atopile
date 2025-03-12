import os
import shutil
import subprocess
import sys
from pathlib import Path
from subprocess import run

import pytest

from faebryk.libs.util import run_live


@pytest.fixture()
def from_temp_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)

    yield

    shutil.rmtree(tmp_path)
    monkeypatch.undo()


@pytest.mark.slow
@pytest.mark.parametrize("config", ["ato", "fab"])
def test_app(config):
    _, stderr, _ = run_live(
        [sys.executable, "-m", "atopile", "build", "examples", "-b", config],
        env={**os.environ, "NONINTERACTIVE": "1"},
        stdout=print,
        stderr=print,
    )
    assert "Build successful!" in stderr
    assert "ERROR" not in stderr


@pytest.mark.xfail(reason="Absolute performance will vary w/ hardware")
@pytest.mark.benchmark(
    min_rounds=10,
    max_time=0.3,
)
def test_snappiness(benchmark):
    def run_cli():
        return run(
            [sys.executable, "-m", "atopile", "--help"],
            capture_output=True,
            text=True,
            env={**os.environ, "NONINTERACTIVE": "1"},
        )

    result = benchmark(run_cli)
    assert result.returncode == 0


@pytest.mark.usefixtures("from_temp_dir")
def test_create_project():
    PROJECT_NAME = "hil_tester"
    process = subprocess.run(
        [sys.executable, "-m", "atopile", "create", "project"],
        capture_output=True,
        text=True,
        env={**os.environ, "NONINTERACTIVE": "1"},
    )
    assert process.returncode == 0
    assert f'Created new project "{PROJECT_NAME}"' in process.stdout

    proj_dir = Path(PROJECT_NAME)
    assert proj_dir.exists() and proj_dir.is_dir()
    assert (proj_dir / "main.ato").is_file()
    assert (proj_dir / "README.md").is_file()
    assert (proj_dir / "ato.yaml").is_file()
    assert (proj_dir / ".github").is_dir()
