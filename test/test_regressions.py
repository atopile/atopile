import os
import shutil
import sys
from pathlib import Path
from subprocess import CalledProcessError

import git
import pathvalidate
import pytest

from faebryk.libs.util import repo_root as _repo_root
from faebryk.libs.util import robustly_rm_dir, run_live


class CloneError(Exception):
    """Failed to clone the repository."""


class InstallError(Exception):
    """Failed to install the project."""


class BuildError(Exception):
    """Failed to build the project."""


def build_project(prj_path: Path, request: pytest.FixtureRequest):
    """Generically "build" the project."""
    friendly_node_name = pathvalidate.sanitize_filename(str(request.node.name))
    artifact_dir = _repo_root() / "artifacts"
    profile_path = artifact_dir / (friendly_node_name + "-profile.html")

    try:
        ato_build_args = [
            "--keep-picked-parts",
            "--keep-net-names",
        ]
        ato_build_env = {"NONINTERACTIVE": "1"}
        run_live(
            [
                sys.executable,
                "-m",
                "pyinstrument",
                "--html",
                "-o",
                profile_path,
                "-i",
                "0.01",
                "-m",
                "atopile",
                "-v",
                "build",
                *ato_build_args,
            ],
            env={**os.environ, **ato_build_env},
            cwd=prj_path,
            stdout=print,
            stderr=print,
        )
    except CalledProcessError as ex:
        artifact_path = artifact_dir / friendly_node_name
        if artifact_path.exists():
            robustly_rm_dir(artifact_path)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(prj_path, artifact_path, ignore=shutil.ignore_patterns(".git"))

        # Translate the error message to clearly distinguish from clone errors
        raise BuildError from ex


@pytest.mark.slow
@pytest.mark.regression
@pytest.mark.parametrize(
    "repo_uri, xfail_reason, multipackage",
    [
        ("https://github.com/atopile/spin-servo-drive", "Known issue", None),
        ("https://github.com/atopile/esp32-s3", "Known issue", None),
        ("https://github.com/atopile/cell-sim", "Known issue", None),
        ("https://github.com/atopile/hil", None, None),
        ("https://github.com/atopile/rp2040", "Known issue", None),
        ("https://github.com/atopile/tca9548apwr", "Known issue", None),
        ("https://github.com/atopile/nau7802", "Known issue", None),
        ("https://github.com/atopile/lv2842xlvddcr", "Known issue", None),
        ("https://github.com/atopile/bq24045dsqr", "Known issue", None),
        ("https://github.com/atopile/packages", None, "packages"),
    ],
)
def test_projects(
    repo_uri: str,
    xfail_reason: str | None,
    multipackage: str | None,
    tmp_path: Path,
    request: pytest.FixtureRequest,
):
    # Clone the repository
    # Using gh to use user credentials if run locally
    try:
        run_live(
            ["gh", "repo", "clone", repo_uri, "project", "--", "--depth", "1"],
            cwd=tmp_path,
            stdout=print,
            stderr=print,
        )
    except CalledProcessError as ex:
        raise CloneError from ex

    prj_path = tmp_path / "project"

    def run_project(path: Path):
        # Generically "install" the project
        try:
            ato_dir = path / ".ato"
            if ato_dir.exists():
                robustly_rm_dir(ato_dir)
            run_live(
                [sys.executable, "-m", "atopile", "-v", "sync"],
                env={**os.environ, "NONINTERACTIVE": "1"},
                cwd=path,
                stdout=print,
                stderr=print,
            )
        except CalledProcessError as ex:
            # Translate the error message to clearly distinguish from clone errors
            raise InstallError from ex

            build_project(path, request=request)

    try:
        if multipackage:
            subpath = prj_path / multipackage
            for subdir in subpath.iterdir():
                if subdir.is_dir():
                    run_project(subdir)
        else:
            run_project(prj_path)
    except (InstallError, BuildError):
        if xfail_reason:
            pytest.xfail(xfail_reason)
        else:
            raise

    repo = git.Repo(prj_path)
    diff = repo.index.diff(None)
    if diff and any(item.a_path.endswith(".kicad_pcb") for item in diff):
        pytest.xfail("can't build with --frozen yet")
