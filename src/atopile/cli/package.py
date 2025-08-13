import logging
import os
from typing import TYPE_CHECKING, Annotated, Iterator

import typer
from pydantic import HttpUrl
from semver import Version

from atopile.errors import UserBadParameterError, UserException, UserFileNotFoundError
from atopile.telemetry import capture
from faebryk.libs.exceptions import accumulate

if TYPE_CHECKING:
    from atopile.config import Config

# Set up logging
logger = logging.getLogger(__name__)

package_app = typer.Typer(rich_markup_mode="rich")


FROM_GIT = "from-git"


def _yield_semver_tags(config: "Config") -> Iterator[Version]:
    from git import Repo

    repo = Repo(config.project.paths.root)
    for tag in repo.tags:
        if not tag.commit == repo.head.commit:
            continue

        try:
            yield Version.parse(tag.name.removeprefix("v"))
        except ValueError:
            continue


def _apply_version(specd_version: str, config: "Config") -> None:
    if specd_version == FROM_GIT:
        try:
            semver_tags = list(_yield_semver_tags(config))
        except Exception as e:
            raise UserException(
                "Could not determine version from git tags: %s" % e
            ) from e

        if len(semver_tags) == 0:
            raise UserBadParameterError("No semver tags found for the current commit")

        elif len(semver_tags) > 1:
            raise UserBadParameterError(
                "Multiple semver tags found for the current commit: %s."
                " No guessing which to use."
            )

        version = semver_tags[0]

    else:
        try:
            version = Version.parse(specd_version.removeprefix("v"))
        except ValueError as ex:
            raise UserBadParameterError(
                f"{specd_version} is not a valid semantic version"
            ) from ex

    if version.prerelease or version.build:
        raise UserBadParameterError(
            "Version must be a semantic version, without prerelease or build."
            f" Got {str(version)}"
        )

    assert config.project.package is not None
    config.project.package.version = str(version)


def _verify_ato_yaml(config: "Config"):
    if config.project.package is None:
        raise UserException(
            "Project has no package configuration. "
            "Please add a `package` section to your `ato.yaml` file."
        )
    if not config.project.package.identifier:
        raise UserBadParameterError(
            "Project `identifier` is not set. Set via ATO_PACKAGE_IDENTIFIER "
            "envvar or in `ato.yaml`"
        )
    if not config.project.package.repository:
        raise UserBadParameterError(
            "Project `repository` is not set. Set via ATO_PACKAGE_REPOSITORY "
            "envvar or in `ato.yaml`"
        )


def _verify_pinned_dependencies(config: "Config", latest: bool = False):
    from atopile.config import RegistryDependencySpec
    from faebryk.libs.backend.packages.api import PackagesAPIClient

    if not config.project.dependencies:
        return

    api = PackagesAPIClient()

    registry_deps = [
        dep
        for dep in config.project.dependencies
        if isinstance(dep, RegistryDependencySpec)
    ]
    unpublishable_deps = [
        dep
        for dep in config.project.dependencies
        if not isinstance(dep, RegistryDependencySpec)
    ]

    for dep in registry_deps:
        if dep.release is None:
            raise UserBadParameterError(
                f"Dependency {dep.identifier} is not pinned to a release."
            )
        if latest and dep.release != api.get_package(dep.identifier).info.version:
            raise UserBadParameterError(
                f"Dependency {dep.identifier} is not at latest version {dep.release}."
            )

    if len(unpublishable_deps) > 0:
        raise UserBadParameterError(
            "Packages can not be published with github or file dependencies: "
            + ", ".join([f"{dep.identifier}" for dep in unpublishable_deps])
        )


def _verify_file_structure(config: "Config"):
    """
    Validate folder & naming conventions for first-party packages.
    Raises UserBadParameterError if any rule is violated.
    """
    from pathlib import Path

    project_root: Path = config.project.paths.root

    if config.project.package is None:
        raise UserException(
            "Project has no package configuration. "
            "Please add a `package` section to your `ato.yaml` file."
        )
    expected_dirname = config.project.package.identifier.split("/")[-1]
    if project_root.name != expected_dirname:
        raise UserBadParameterError(
            f"Project directory '{project_root.name}' must be named "
            f"'{expected_dirname}'"
        )

    # 2. Required top-level files / dirs
    required = [
        project_root / "ato.yaml",
        project_root / f"{expected_dirname}.ato",
        project_root / "layouts",
        project_root / "parts",
        project_root / "README.md",
    ]
    missing = [str(p.relative_to(project_root)) for p in required if not p.exists()]
    if missing:
        raise UserBadParameterError(
            "Missing required files/directories: " + ", ".join(missing)
        )

    # 3. ato.yaml must contain both 'default' and 'usage' builds
    build_names = set(config.project.builds.keys())
    for required_build in {"default", "usage"}:
        if required_build not in build_names:
            raise UserBadParameterError(
                f"ato.yaml must define a '{required_build}' build target"
            )

    # 4. Build settings requirements
    for build_cfg in config.project.builds.values():
        if build_cfg.hide_designators is not True:
            raise UserBadParameterError(
                "Every build must set 'hide_designators: true' in ato.yaml"
            )
        if "PCB.requires_drc_check" not in set(build_cfg.exclude_checks):
            raise UserBadParameterError(
                "Every build must include 'exclude_checks: ['PCB.requires_drc_check']'"
            )


def _verify_build_exists(config: "Config"):
    missing_builds = [
        b
        for b in config.project.builds.keys()
        if not config.project.paths.root.joinpath("build", "builds").exists()
    ]
    if missing_builds:
        raise UserFileNotFoundError(
            "Missing build directories: "
            + ", ".join(missing_builds)
            + " Please run `ato build` to create the build directories."
        )


def _verify_3d_models(config: "Config"):
    from pathlib import Path

    from faebryk.libs.kicad.fileformats_version import (
        try_load_kicad_pcb_file,
    )

    layout_path: Path = config.project.paths.layout
    kicad_pcb_paths = list(layout_path.rglob("*.kicad_pcb"))

    missing_models: list[str] = []

    def _resolve_model_path(raw: Path, pcb_dir: Path) -> Path:
        s = str(raw)
        s = s.replace("${KIPRJMOD}", str(pcb_dir))
        s = os.path.expandvars(s)
        p = Path(s)
        if p.is_absolute():
            return p
        return pcb_dir / p

    for pcb_path in kicad_pcb_paths:
        pcb_file = try_load_kicad_pcb_file(pcb_path)
        pcb_dir = pcb_path.parent
        for fp in pcb_file.kicad_pcb.footprints:
            for m in getattr(fp, "models", []):
                resolved = _resolve_model_path(m.path, pcb_dir)
                if not resolved.exists():
                    missing_models.append(
                        f"{pcb_path.relative_to(config.project.paths.root)} -> "
                        f"{m.path} -> {resolved}"
                    )

    if missing_models:
        raise UserBadParameterError(
            "Missing 3D model files referenced in KiCad boards:\n\n"
            + "\n".join(missing_models)
        )


def _verify_no_warnings(config: "Config"):
    logs_latest = config.project.paths.logs / "latest"

    if not logs_latest.exists():
        raise UserFileNotFoundError(
            f"Missing logs directory: {logs_latest}. "
            "Please run `ato build` to generate logs."
        )

    offenders: list[str] = []
    for path in logs_latest.rglob("*"):
        if not path.is_file():
            continue
        if "warning" in path.name:
            try:
                if path.stat().st_size > 0:
                    offenders.append(str(path.relative_to(config.project.paths.root)))
            except OSError:
                # If the file can't be stat'ed, count it as an offender to be safe
                offenders.append(str(path.relative_to(config.project.paths.root)))

    if offenders:
        raise UserBadParameterError(
            "Warning logs must be empty. Non-empty warning files found:\n\n"
            + ", ".join(offenders)
        )


def verify_package(config: "Config"):
    if config.project.package is not None:
        strict = config.project.package.repository == HttpUrl(
            "https://github.com/atopile/packages"
        )
    else:
        strict = False

    with accumulate() as accumulator:
        with accumulator.collect():
            _verify_ato_yaml(config)
        with accumulator.collect():
            _verify_build_exists(config)
        with accumulator.collect():
            _verify_pinned_dependencies(config, latest=strict)
        if strict:
            logger.info("Running strict verification")
            with accumulator.collect():
                _verify_3d_models(config)
            with accumulator.collect():
                _verify_file_structure(config)
            with accumulator.collect():
                _verify_no_warnings(config)

    logger.info("Package verification successful! 🎉")


@package_app.command()
@capture("cli:package_publish_start", "cli:package_publish_end")
def publish(
    version: Annotated[
        str,
        typer.Option(
            "--version",
            "-v",
            envvar="ATO_CLI_PACKAGE_VERSION",
            help="The version of the package to publish.",
        ),
    ] = "",
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Dry run the package publication."),
    ] = False,
    package_address: Annotated[
        str | None,
        typer.Argument(help="The address of the package to publish."),
    ] = None,
    include_artifacts: Annotated[
        bool,
        typer.Option(
            "--include-artifacts",
            "-a",
            envvar="ATO_CLI_PACKAGE_INCLUDE_ARTIFACTS",
            help="Include build artifacts in the package.",
        ),
    ] = True,
    skip_auth: Annotated[
        bool,
        typer.Option("--skip-auth", "-s", help="Skip authentication."),
    ] = False,
    skip_duplicate_versions: Annotated[
        bool,
        typer.Option(
            "--skip-duplicate-versions",
            envvar="ATO_CLI_PACKAGE_SKIP_DUPLICATE_VERSIONS",
            help="Ignore duplicate version errors.",
        ),
    ] = False,
):
    """
    Publish a package to the package registry.

    Currently, the only supported authentication method is Github Actions OIDC.

    For the options which allow multiple inputs, use comma separated values.
    """
    import faebryk.libs.backend.packages.api as packages_api
    from atopile.config import config
    from atopile.errors import UserBadParameterError, UserException
    from faebryk.libs.backend.packages.api import PackagesAPIClient
    from faebryk.libs.package.artifacts import Artifacts
    from faebryk.libs.package.dist import Dist, DistValidationError

    # Apply the entry-point early
    # This will configure the project root properly, meaning you can practically spec
    # the working directory of the publish and expands for future use publishing
    # packagelets from specific module entrypoints
    config.apply_options(entry=package_address)
    logger.info("Using project config: %s", config.project.paths.root / "ato.yaml")

    if version:  # NOT `is not None` to allow for empty strings
        _apply_version(version, config)

    if config.project.package is None:
        raise UserException(
            "Project has no package configuration. "
            "Please add a `package` section to your `ato.yaml` file."
        )
    logger.info("Package version: %s", config.project.package.version)

    if not config.project.package.identifier:
        raise UserBadParameterError(
            "Project `identifier` is not set. Set via ATO_PACKAGE_IDENTIFIER envvar"
            " or in `ato.yaml`"
        )

    if not config.project.package.repository:
        raise UserBadParameterError(
            "Project `repository` is not set. Set via ATO_PACKAGE_REPOSITORY envvar"
            " or in `ato.yaml`"
        )

    # Build the package
    try:
        dist = Dist.build_dist(
            cfg=config.project,
            output_path=config.project.paths.build,
        )
    except DistValidationError as e:
        raise UserException(
            "Could not build package distribution: %s" % e
            + "\n Have a look at https://docs.atopile.io/atopile/essentials/4-packages"
        ) from e

    logger.info("Package distribution built: %s", dist.path)

    if include_artifacts:
        artifacts = Artifacts.build_artifacts(
            cfg=config.project, output_path=config.project.paths.build
        )
    else:
        artifacts = None

    try:
        from git import Repo

        repo = Repo(config.project.paths.root)
        git_ref = str(repo.head.ref)
    except Exception:
        git_ref = None

    # Upload sequence
    if dry_run:
        logger.info("Dry run, skipping upload")
    else:
        api = PackagesAPIClient()
        try:
            package_url = api.publish(
                identifier=config.project.package.identifier,
                version=str(config.project.package.version),
                dist=dist,
                artifacts=artifacts,
                git_ref=git_ref,
                skip_auth=skip_auth,
            ).url
        except packages_api.Errors.ReleaseAlreadyExistsError:
            if skip_duplicate_versions:
                logger.info("Release already exists, skipping")
                return
            else:
                raise

        logger.info("Package URL: %s", package_url)

    logger.info("Done! 📦🛳️")


@package_app.command()
@capture("cli:package_verify_start", "cli:package_verify_end")
def verify(
    package_address: Annotated[
        str | None,
        typer.Argument(
            help="Path/to/project or address (file.ato:Module) of the package "
            "you want to verify.",
        ),
    ] = None,
    strict: Annotated[
        bool,
        typer.Option("--strict", "-s", help="Fail on any warning."),
    ] = False,
):
    """
    Validate that a package can be built and meets the registry rules.
    """

    from atopile.config import config

    config.apply_options(entry=package_address)

    verify_package(config)


if __name__ == "__main__":
    from atopile.config import config

    config.apply_options(entry="../packages/packages/archive/indicator-leds")

    verify_package(config)
