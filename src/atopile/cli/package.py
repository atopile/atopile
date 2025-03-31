import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Annotated, Iterator
from urllib.parse import urlparse

import pathspec
import pathvalidate
import requests
import rich.progress
import typer
from git import Repo
from ruamel.yaml import YAML
from semver import Version

import atopile.config
from atopile.config import config
from atopile.errors import UserBadParameterError

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

package_app = typer.Typer(rich_markup_mode="rich")


FROM_GIT = "from-git"


def _get_actions_token(audience: str) -> str:
    logger.debug(f"GH OIDC audience: {audience}")
    # Get a JWT from the Github API
    # https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect#updating-your-actions-for-oidc
    actions_token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    actions_token_url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL")
    if not actions_token or not actions_token_url:
        raise RuntimeError(
            "No actions token found in environment. Check permissions: https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect#adding-permissions-settings"
        )

    r = requests.get(
        actions_token_url + f"&audience={audience}",
        headers={"Authorization": f"bearer {actions_token}"},
    )
    r.raise_for_status()
    return r.json()["value"]


def _yield_semver_tags() -> Iterator[Version]:
    repo = Repo(config.project.paths.root)
    for tag in repo.tags:
        if not tag.commit == repo.head.commit:
            continue

        try:
            yield Version.parse(tag.name)
        except ValueError:
            continue


def _apply_version(specd_version: str) -> None:
    if specd_version == FROM_GIT:
        semver_tags = list(_yield_semver_tags())

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
            version = Version.parse(specd_version)
        except ValueError as ex:
            raise UserBadParameterError(
                f"{specd_version} is not a valid semantic version"
            ) from ex

    if version.prerelease or version.build:
        raise UserBadParameterError(
            "Version must be a semantic version, without prerelease or build."
            f" Got {str(version)}"
        )

    config.project.version = str(version)


def _build_package(
    include_pathspec_list: list[str],
    include_builds_set: set[str],
    output_path: Path,
) -> Path:
    spec = pathspec.PathSpec.from_lines("gitwildmatch", include_pathspec_list)
    matched_files = list(spec.match_tree_files(config.project.paths.root))

    package_filename = (
        pathvalidate.sanitize_filename(
            f"{config.project.name}-{config.project.version}".replace("/", "-")
        )
        + ".zip"
    )

    # TODO: make this ./dist or the likes?
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        zip_path = temp_path / package_filename

        # Create the package config
        package_config_path = temp_path / atopile.config.PROJECT_CONFIG_FILENAME

        yaml = YAML(typ="rt")  # round-trip
        with (config.project_dir / atopile.config.PROJECT_CONFIG_FILENAME).open(
            "r", encoding="utf-8"
        ) as file:
            config_data: dict = yaml.load(file) or {}

        config_data["name"] = config.project.name
        config_data["repository"] = config.project.repository
        config_data["version"] = str(config.project.version)

        config_data["builds"] = {
            k: v for k, v in config_data["builds"].items() if k in include_builds_set
        }

        with package_config_path.open("w", encoding="utf-8") as file:
            yaml.dump(config_data, file)

        ## Validate the package config is a valid config at all
        try:
            atopile.config.ProjectConfig.from_path(package_config_path)
        except Exception as e:
            raise UserBadParameterError(
                "Something went wrong while validating the package config. "
                "Please check the config file."
            ) from e

        # Bundle up the package
        with zipfile.ZipFile(zip_path, "x") as zip_file:
            ## Copy in the freshly minted package config
            zip_file.write(package_config_path, atopile.config.PROJECT_CONFIG_FILENAME)

            ## Copy in the files to package
            for file in rich.progress.track(
                matched_files, description="Building package..."
            ):
                src_path = config.project.paths.root / file
                if not src_path.is_file():
                    continue

                if file == "ato.yaml":
                    continue

                zip_file.write(src_path, file)

        shutil.copy(zip_path, output_path)

        return output_path


@package_app.command()
def publish(
    include_pathspec: Annotated[
        str,
        typer.Option(
            "--include",
            "-i",
            envvar="ATO_PACKAGE_INCLUDE_PATCHSPEC",
            help="Comma separated globs to files to include in the package",
        ),
    ],
    include_builds: Annotated[
        str,
        typer.Option(
            "--include-build",
            "-b",
            envvar="ATO_PACKAGE_INCLUDE_BUILD",
            help=(
                "Comma separated build-targets to include in the package. "
                "An empty string implies all build-targets."
            ),
        ),
    ] = "",
    version: Annotated[
        str,
        typer.Option(
            "--version",
            "-v",
            envvar="ATO_PACKAGE_VERSION",
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
):
    """
    Publish a package to the package registry.

    Currently, the only supported authentication method is Github Actions OIDC.

    For the options which allow multiple inputs, use comma separated values.
    """

    include_pathspec_list = [p.strip() for p in include_pathspec.split(",")]

    if include_builds:
        include_builds_set = set([t.strip() for t in include_builds.split(",")])
    else:
        include_builds_set = set(config.project.builds)

    # Apply the entry-point early
    # This will configure the project root properly, meaning you can practically spec
    # the working directory of the publish and expands for future use publishing
    # packagelets from specific module entrypoints
    config.apply_options(entry=package_address)
    logger.info("Using project config: %s", config.project.paths.root / "ato.yaml")

    if version:  # NOT `is not None` to allow for empty strings
        _apply_version(version)
    logger.info("Package version: %s", config.project.version)

    if not config.project.name:
        raise UserBadParameterError(
            "Project `name` is not set. Set via ENVVAR or in `ato.yaml`"
        )

    if not config.project.repository:
        raise UserBadParameterError(
            "Project `repository` is not set. Set via ENVVAR or in `ato.yaml`"
        )

    missing_builds = include_builds_set - set(config.project.builds)
    if missing_builds:
        raise UserBadParameterError("Builds not found: %s" % ", ".join(missing_builds))

    # Build the package
    package_path = _build_package(
        include_pathspec_list, include_builds_set, config.project.paths.build
    )
    logger.info("Package built: %s", package_path)

    # Upload sequence
    if dry_run:
        logger.info("Dry run, skipping upload")
    else:
        ## Get authorization
        jwt = _get_actions_token(urlparse(config.project.services.packages.url).netloc)

        ## Request upload
        upload_endpoint = "/v1/upload/request"
        r = requests.post(
            f"{config.project.services.packages.url}{upload_endpoint}",
            headers={"Authorization": f"bearer {jwt}"},
            json={"package_version": str(config.project.version), "manifest": {}},
        )
        r.raise_for_status()

        ## Upload the package
        # TODO:

        ## Confirm upload
        # TODO:

    logger.info("Done! 📦🛳️")
