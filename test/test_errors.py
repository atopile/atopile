import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from atopile import errors
from atopile.build import _init_python_app
from atopile.config import config

PROJECT_DIR = Path("test/common/resources/test-project")


@pytest.fixture()
def from_project_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    tmp_project_dir = tmp_path / "test-project"
    shutil.copytree(PROJECT_DIR, tmp_project_dir)
    monkeypatch.chdir(tmp_project_dir)

    yield

    shutil.rmtree(tmp_project_dir)
    monkeypatch.undo()


@pytest.mark.parametrize(
    "build_name,expected_error",
    [
        ("unconstructable", errors.UserPythonConstructionError),
        ("unimportable", errors.UserPythonModuleError),
    ],
)
@pytest.mark.usefixtures("from_project_dir")
def test_build_errors(build_name: str, expected_error):
    config.project_dir = Path.cwd()
    config.selected_builds = [build_name]

    with pytest.raises(expected_error) as exc_info, next(config.builds):
        _init_python_app()

    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, ValueError)
    assert exc_info.value.__cause__.args == (build_name,)


@pytest.mark.parametrize("build_name", ["unconstructable", "unimportable"])
@pytest.mark.usefixtures("from_project_dir")
def test_build_error_logging(build_name: str):
    process = subprocess.run(
        [sys.executable, "-m", "atopile", "build", "-b", build_name],
        capture_output=True,
        text=True,
        env={**os.environ, "NONINTERACTIVE": "1"},
    )

    # single error
    assert process.stderr.count("ERROR") == 1

    # single traceback
    assert process.stderr.count("❱") == 1
    assert process.stderr.count("Traceback (most recent call last)") == 1
    assert "another exception occurred" not in process.stderr
    assert "direct cause of the following exception" not in process.stderr

    # including the test exception
    assert f'raise ValueError("{build_name}")' in process.stderr

    # exiting cleanly
    expected_ending = (
        "Unfortunately errors ^^^ stopped the build. If you need a"
        " hand jump on Discord! https://discord.gg/CRe5xaDBr3 👋"
    )
    actual_ending = process.stdout.strip().replace("\n", "")
    assert actual_ending.endswith(expected_ending)

    # exception groups are unwrapped
    assert "ExceptionGroup" not in process.stderr

    # with a non-zero exit code
    assert process.returncode == 1
