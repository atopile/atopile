import logging
import os
from typing import Annotated
from urllib.parse import urlparse

import requests
import typer
from semver import Version

from atopile.config import config
from atopile.errors import UserBadParameterError

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

package_app = typer.Typer(rich_markup_mode="rich")


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


@package_app.command()
def publish(
    include_paths: Annotated[
        str,
        typer.Option(
            "--include",
            "-i",
            envvar="ATO_PACKAGE_INCLUDE",
            help="Comma separated globs to files to include in the package",
        ),
    ],
    exclude_paths: Annotated[
        str,
        typer.Option(
            "--exclude",
            "-e",
            envvar="ATO_PACKAGE_EXCLUDE",
            help=(
                "Comma separated globs to files to exclude from the package. "
                "An empty string implies no exclusions."
            ),
        ),
    ] = "",
    include_targets: Annotated[
        str,
        typer.Option(
            "--include-build-targets",
            "-b",
            envvar="ATO_PACKAGE_INCLUDE_BUILD_TARGETS",
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
    ] = "from-git",
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Dry run the package publication."),
    ] = False,
):
    """
    Publish a package to the package registry.

    Currently, the only supported authentication method is Github Actions OIDC.

    For the options which allow multiple inputs, use comma separated values.
    """

    # Stage 0. Validate and parse inputs
    include_paths_list = [p.strip() for p in include_paths.split(",")]
    exclude_paths_list = [p.strip() for p in exclude_paths.split(",")]
    include_targets_list = [t.strip() for t in include_targets.split(",")]

    bad_semver_ex = UserBadParameterError(
        "Version must be a semantic version, without prerelease or build"
    )
    try:
        package_version_semver = Version.parse(version)
    except ValueError as ex:
        raise bad_semver_ex from ex

    if package_version_semver.prerelease or package_version_semver.build:
        raise bad_semver_ex

    # Stage 1. Obtain authorization
    jwt = _get_actions_token(urlparse(config.project.services.packages.url).netloc)

    # Stage 2. Request upload - this confirms things like package metadata
    upload_endpoint = "/v1/upload/request"
    r = requests.post(
        f"{config.project.services.packages.url}{upload_endpoint}",
        headers={"Authorization": f"bearer {jwt}"},
        json={"package_version": package_version_semver, "manifest": {}},
    )
    r.raise_for_status()

    # Stage 3. Upload the package to the presigned upload URL
    # TODO: Implement this
