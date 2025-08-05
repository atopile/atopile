import logging
from typing import TYPE_CHECKING, Annotated, Iterator

import typer
from semver import Version

from atopile.errors import UserBadParameterError, UserException
from atopile.telemetry import capture

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
