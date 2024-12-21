import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from atopile import errors
from atopile.cli.build import _init_python_app
from atopile.cli.common import create_build_contexts

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
    build_ctxs = create_build_contexts(
        entry=None, build=[build_name], target=[], option=[], standalone=False
    )

    (build_ctx,) = build_ctxs

    with pytest.raises(expected_error) as exc_info:
        _init_python_app(build_ctx)

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
        env={**os.environ, "ATO_NON_INTERACTIVE": "1"},
    )

    # single error
    assert process.stdout.count("ERROR") == 1

    # single traceback
    assert process.stdout.count("❱") == 1
    assert process.stdout.count("Traceback (most recent call last)") == 1
    assert "another exception occurred" not in process.stdout
    assert "direct cause of the following exception" not in process.stdout

    # including the test exception
    assert f'raise ValueError("{build_name}")' in process.stdout

    # exiting cleanly
    expected_ending = (
        "Unfortunately errors ^^^ stopped the build. If you need a"
        " hand jump on Discord! https://discord.gg/mjtxARsr9V 👋"
    )
    actual_ending = process.stdout.strip().replace("\n", "")
    assert actual_ending.endswith(expected_ending)

    # exception groups are unwrapped
    assert "ExceptionGroup" not in process.stdout

    # with a non-zero exit code
    assert process.returncode == 1
