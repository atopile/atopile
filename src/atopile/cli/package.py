import logging
import os
from typing import Annotated

import requests
import typer

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

package_app = typer.Typer(rich_markup_mode="rich")


def _get_actions_token(audience: str) -> str:
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
    ],
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
    registry: Annotated[
        str,
        typer.Option(
            "--registry",
            "-r",
            envvar="ATO_PACKAGE_REGISTRY",
            help="The registry to publish the package to.",
        ),
    ] = "https://packages.atopileapi.com",
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

    # Stage 1. Obtain authorization
    jwt = _get_actions_token(
        "packages.atopileapi.com"
    )  # FIXME: pull from registry domain

    # Stage 2. Request upload - this confirms things like package metadata
    upload_endpoint = "/v0/package-upload-request"
    r = requests.post(
        f"{registry}{upload_endpoint}",
        headers={"Authorization": f"bearer {jwt}"},
        json={"version": "1.2.3", "manifest": {}},
    )
    r.raise_for_status()

    # print for debugging
    print(r.json())

    # Stage 3. Upload the package to the presigned upload URL
    # TODO: Implement this
