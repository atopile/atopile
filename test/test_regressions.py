import os
import shutil
import sys
from pathlib import Path
from subprocess import CalledProcessError

import pathvalidate
import pytest

from faebryk.libs.util import robustly_rm_dir, run_live

repo_root = Path.cwd()
while not (repo_root / "pyproject.toml").exists():
    repo_root = repo_root.parent


EXAMPLES_DIR = repo_root / "examples"


@pytest.mark.slow
@pytest.mark.regression
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


class CloneError(Exception):
    """Failed to clone the repository."""


class InstallError(Exception):
    """Failed to install the project."""


class BuildError(Exception):
    """Failed to build the project."""


@pytest.mark.slow
@pytest.mark.regression
@pytest.mark.parametrize(
    "repo, env",
    [
        ("https://github.com/atopile/spin-servo-drive", {}),
        ("https://github.com/atopile/esp32-s3", {}),
        ("https://github.com/atopile/nonos", {}),
        (
            "https://github.com/atopile/cell-sim",
            {
                # TODO: @lazy-mifs remove this
                "FBRK_MAX_PATHS": "1e7",
                "FBRK_MAX_PATHS_NO_WEAK": "1e6",
                "FBRK_MAX_PATHS_NO_NEW_WEAK": "1e5",
            },
        ),
        ("https://github.com/atopile/rp2040", {}),
        ("https://github.com/atopile/tca9548apwr", {}),
        ("https://github.com/atopile/nau7802", {}),
        ("https://github.com/atopile/lv2842xlvddcr", {}),
        ("https://github.com/atopile/bq24045dsqr", {}),
    ],
)
def test_projects(
    repo: str, env: dict[str, str], tmp_path: Path, request: pytest.FixtureRequest
):
    # Clone the repository
    # Using gh to use user credentials if run locally
    try:
        run_live(
            ["gh", "repo", "clone", repo, "project", "--", "--depth", "1"],
            cwd=tmp_path,
            stdout=print,
            stderr=print,
        )
    except CalledProcessError as ex:
        raise CloneError from ex

    prj_path = tmp_path / "project"

    # Generically "install" the project
    try:
        run_live(
            [sys.executable, "-m", "atopile", "-v", "install"],
            env={**os.environ, "ATO_NON_INTERACTIVE": "1", **env},
            cwd=prj_path,
            stdout=print,
            stderr=print,
        )
    except CalledProcessError as ex:
        # Translate the error message to clearly distinguish from clone errors
        raise InstallError from ex

    # Generically "build" the project
    try:
        run_live(
            [sys.executable, "-m", "atopile", "-v", "build", "--frozen"],
            env={**os.environ, "ATO_NON_INTERACTIVE": "1", **env},
            cwd=prj_path,
            stdout=print,
            stderr=print,
        )
    except CalledProcessError as ex:
        artifact_path = (
            repo_root
            / "artifacts"
            / pathvalidate.sanitize_filename(str(request.node.name))
        )
        if artifact_path.exists():
            robustly_rm_dir(artifact_path)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(prj_path, artifact_path, ignore=shutil.ignore_patterns(".git"))

        # Translate the error message to clearly distinguish from clone errors
        raise BuildError from ex
