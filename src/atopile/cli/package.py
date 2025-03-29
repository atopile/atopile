import logging
import os
from pathlib import Path
from typing import Annotated

import requests
import typer

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

package_app = typer.Typer(rich_markup_mode="rich")


@package_app.command()
def build(
    include_paths: Annotated[
        list[Path],
        typer.Option(
            "--include", "-i", help="Paths to files to include in the package"
        ),
    ],
    exclude_paths: Annotated[
        list[Path],
        typer.Option(
            "--exclude", "-e", help="Paths to files to exclude from the package"
        ),
    ],
    include_targets: Annotated[
        list[str],
        typer.Option(
            "--include-targets", "-t", help="Targets to include in the package"
        ),
    ],
):
    """
    Package an atopile project for publishing to the package registry.
    """
    raise NotImplementedError(
        "Not implemented - currently only manually packed projects are supported"
    )


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
        actions_token_url + f"&audience={audience}", auth=("bearer", actions_token)
    )
    r.raise_for_status()
    return r.json()["value"]


@package_app.command()
def publish(
    package: Annotated[Path, typer.Option("--package", "-p")],
    registry: Annotated[
        str, typer.Option("--registry", "-r")
    ] = "https://packages.atopileapi.com",
):
    """
    Publish a package to the package registry.

    Currently, the only supported authentication method is Github Actions OIDC.
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
