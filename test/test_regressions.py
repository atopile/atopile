import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from subprocess import CalledProcessError

import git
import pathvalidate
import pytest

from faebryk.libs.util import not_none, robustly_rm_dir, run_live
from faebryk.libs.util import repo_root as _repo_root


class CloneError(Exception):
    """Failed to clone the repository."""


class InstallError(Exception):
    """Failed to install the project."""


class BuildError(Exception):
    """Failed to build the project."""


ENABLE_PROFILING = False

# Directories to skip when discovering packages in a multipackage repo
SKIP_PACKAGE_DIRS = {"archive", "logos", ".git", "__pycache__"}


def clone_repo(repo_uri: str, path: Path):
    """Clone a repository without depending on the GitHub CLI."""
    if not Path(repo_uri).exists() and not repo_uri.startswith(
        ("https://", "ssh://", "git@")
    ):
        repo_uri = f"https://github.com/{repo_uri}"
    run_live(
        ["git", "clone", "--depth", "1", repo_uri, str(path)],
        cwd=path.parent,
        stdout=print,
        stderr=print,
    )


def build_project(prj_path: Path, request: pytest.FixtureRequest):
    """Generically "build" the project."""
    friendly_node_name = pathvalidate.sanitize_filename(str(request.node.name))
    artifact_dir = _repo_root() / "artifacts"

    try:
        ato_build_args = [
            # "--keep-picked-parts", # not supported on new core yet
            # "--keep-net-names",
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
                "build",
                "-v",
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


def sync_project(path: Path):
    """Run ato sync on a project."""
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
        raise InstallError from ex


@dataclass
class _TestRepo:
    repo_uri: str
    skip_reason: str | None = None
    multipackage: str | None = None

    def __post_init__(self):
        if not self.repo_uri.startswith("https") and not self.repo_uri.startswith(
            "ssh"
        ):
            self.repo_uri = f"https://github.com/{self.repo_uri}"

    def skip(self, reason: str):
        self.skip_reason = reason
        return self


@dataclass(frozen=True)
class _ProjectTest:
    repo_uri: str
    project_path: str = "."
    skip_reason: str | None = None


def _project_test_id(test_cfg: _ProjectTest) -> str:
    if test_cfg.project_path == ".":
        return test_cfg.repo_uri
    return f"{test_cfg.repo_uri}/{test_cfg.project_path}"


SINGLE_PROJECTS: list[_ProjectTest] = [
    _ProjectTest("atopile/spin-servo-drive", skip_reason="Needs upgrading"),
    _ProjectTest("atopile/atopile", "examples/auto-picking"),
    _ProjectTest("atopile/atopile", "examples/equations"),
    _ProjectTest("atopile/atopile", "examples/esp32_minimal"),
    _ProjectTest("atopile/atopile", "examples/fabll_minimal"),
    _ProjectTest("atopile/atopile", "examples/i2c"),
    _ProjectTest("atopile/atopile", "examples/layout_reuse"),
    _ProjectTest("atopile/atopile", "examples/led_badge"),
    _ProjectTest("atopile/atopile", "examples/quickstart"),
]

# Multipackage repo configuration
PACKAGES_REPO = _TestRepo("atopile/packages", multipackage="packages")

# Known failing packages with their skip reasons
# Add package names here with reasons to mark them as expected to be skipped
KNOWN_FAILING_PACKAGES: dict[str, str] = {
    # Example: "package-name": "Reason for expected failure",
}


def _discover_packages(packages_path: Path) -> list[str]:
    """Discover package names from a packages directory."""
    if not packages_path.exists() or not packages_path.is_dir():
        return []

    packages = []
    for subdir in sorted(packages_path.iterdir()):
        if (
            subdir.is_dir()
            and subdir.name not in SKIP_PACKAGE_DIRS
            and not subdir.name.endswith(".md")
            and (subdir / "ato.yaml").exists()
        ):
            packages.append(subdir.name)

    return packages


def _get_local_packages_repo_path() -> Path | None:
    """Return the provisioned sibling packages repo if present."""
    multipackage_subdir = not_none(PACKAGES_REPO.multipackage)
    repo_path = _repo_root().parent / "packages"
    if not repo_path.exists() or not (repo_path / ".git").exists():
        return None
    if not (repo_path / multipackage_subdir).exists():
        return None
    return repo_path


@pytest.fixture(scope="session")
def packages_repo_path() -> Path:
    """
    Session-scoped fixture that provides the packages repo path.

    Uses the provisioned sibling packages repo.
    """
    repo_path = _get_local_packages_repo_path()
    if repo_path is None:
        pytest.skip("packages repo not provisioned at ../packages")
    return repo_path


@pytest.fixture(scope="session")
def project_repo_paths(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Clone each external project repo once per test session."""
    cache_dir = tmp_path_factory.mktemp("project-repos")
    repo_paths: dict[str, Path] = {}
    for repo_uri in sorted({test.repo_uri for test in SINGLE_PROJECTS}):
        repo_path = cache_dir / repo_uri.replace("/", "__")
        try:
            clone_repo(repo_uri, repo_path)
        except CalledProcessError as ex:
            raise CloneError(f"Failed to clone {repo_uri}") from ex
        repo_paths[repo_uri] = repo_path
    return repo_paths


# ============================================================================
# Single-project regression tests
# ============================================================================


@pytest.mark.slow
@pytest.mark.regression
@pytest.mark.parametrize("test_cfg", SINGLE_PROJECTS, ids=_project_test_id)
def test_single_projects(
    test_cfg: _ProjectTest,
    project_repo_paths: dict[str, Path],
    tmp_path: Path,
    request: pytest.FixtureRequest,
):
    """Test single-project repositories (not multipackage)."""
    repo_path = project_repo_paths[test_cfg.repo_uri]
    test_repo_path = tmp_path / "project"
    shutil.copytree(repo_path, test_repo_path)

    prj_path = test_repo_path / test_cfg.project_path

    try:
        sync_project(prj_path)
        build_project(prj_path, request=request)
    except (InstallError, BuildError):
        if test_cfg.skip_reason:
            pytest.skip(f"xfail: {test_cfg.skip_reason}")
        else:
            raise

    repo = git.Repo(test_repo_path)
    diff = repo.index.diff(None)
    if diff and any(
        item.a_path is not None and item.a_path.endswith(".kicad_pcb") for item in diff
    ):
        pytest.skip("xfail: can't build with --frozen yet")


# ============================================================================
# Multipackage (atopile/packages) regression tests
# ============================================================================


def pytest_generate_tests(metafunc: pytest.Metafunc):
    """Generate test parameters for package tests at collection time."""
    if "package_name" not in metafunc.fixturenames:
        return

    repo_path = _get_local_packages_repo_path()
    multipackage_subdir = not_none(PACKAGES_REPO.multipackage)
    packages = (
        _discover_packages(repo_path / multipackage_subdir)
        if repo_path is not None
        else []
    )

    if packages:
        params = []
        for pkg_name in packages:
            skip_reason = KNOWN_FAILING_PACKAGES.get(pkg_name)
            marks = [pytest.mark.skip(reason="xfail")] if skip_reason else []
            params.append(
                pytest.param(pkg_name, id=f"packages/{pkg_name}", marks=marks)
            )
        metafunc.parametrize("package_name", params)
    else:
        # No packages found - skip parameterization, test will handle it
        metafunc.parametrize("package_name", [pytest.param(None, id="no-packages")])


@pytest.mark.slow
@pytest.mark.regression
@pytest.mark.packages
def test_package(
    package_name: str | None,
    packages_repo_path: Path,
    tmp_path: Path,
    request: pytest.FixtureRequest,
):
    """
    Test a single package from the atopile/packages repo.
    """
    multipackage_subdir = not_none(PACKAGES_REPO.multipackage)

    if package_name is None:
        pytest.skip("No packages found in repo")

    source_package_path = packages_repo_path / multipackage_subdir / package_name
    if not source_package_path.exists():
        pytest.skip(f"Package {package_name} not found in cloned repo")

    test_package_path = tmp_path / package_name
    shutil.copytree(
        source_package_path,
        test_package_path,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
    )

    skip_reason = KNOWN_FAILING_PACKAGES.get(package_name)

    try:
        sync_project(test_package_path)
        build_project(test_package_path, request=request)
    except (InstallError, BuildError):
        if skip_reason:
            pytest.skip(f"xfail: {skip_reason}")
        else:
            raise
