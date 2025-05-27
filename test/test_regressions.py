import os
import shutil
import sys
from dataclasses import dataclass
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


ENABLE_PROFILING = False


def build_project(prj_path: Path, request: pytest.FixtureRequest):
    """Generically "build" the project."""
    friendly_node_name = pathvalidate.sanitize_filename(str(request.node.name))
    artifact_dir = _repo_root() / "artifacts"

    try:
        ato_build_args = [
            "--keep-picked-parts",
            "--keep-net-names",
        ]
        ato_build_env = {"NONINTERACTIVE": "1"}

        profile = []
        if ENABLE_PROFILING:
            profile_path = artifact_dir / (friendly_node_name + "-profile.html")
            profile = [
                "-m",
                "pyinstrument",
                "--html",
                "-o",
                profile_path,
                "-i",
                "0.01",
            ]
        run_live(
            [
                sys.executable,
                *profile,
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


@dataclass
class _TestRepo:
    repo_uri: str
    xfail_reason: str | None = None
    multipackage: str | None = None

    def __post_init__(self):
        if not self.repo_uri.startswith("https") and not self.repo_uri.startswith(
            "ssh"
        ):
            self.repo_uri = f"https://github.com/{self.repo_uri}"

    def xfail(self, reason: str):
        self.xfail_reason = reason
        return self


REPOS = [
    _TestRepo("atopile/spin-servo-drive").xfail("Needs upgrading"),
    _TestRepo("atopile/packages", multipackage="packages"),
]


@pytest.mark.slow
@pytest.mark.regression
@pytest.mark.parametrize(
    "test_cfg",
    REPOS,
    ids=lambda x: x.repo_uri,
)
def test_projects(
    test_cfg: _TestRepo,
    tmp_path: Path,
    request: pytest.FixtureRequest,
):
    repo_uri = test_cfg.repo_uri
    xfail_reason = test_cfg.xfail_reason
    multipackage = test_cfg.multipackage

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
    # Check if diff exists and if any item in the diff represents
    # a change to a KiCad PCB file
    if diff and any(
        item.a_path is not None and item.a_path.endswith(".kicad_pcb") for item in diff
    ):
        pytest.xfail("can't build with --frozen yet")
