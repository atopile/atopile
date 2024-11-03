# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

import requests

import faebryk.library._F as F
from faebryk.core.module import Module

logger = logging.getLogger(__name__)


def export_datasheets(
    app: Module,
    path: Path = Path("build/documentation/datasheets"),
    overwrite: bool = False,
):
    """
    Export all datasheets of all modules (that have a datasheet defined)
    of the given application.
    """
    # Create directories if they don't exist
    path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Exporting datasheets to: {path}")
    for m in app.get_children_modules(types=Module):
        if not m.has_trait(F.has_datasheet):
            continue
        url = m.get_trait(F.has_datasheet).get_datasheet()
        if not url:
            logger.warning(f"Missing datasheet URL for {m}")
            continue
        filename = type(m).__name__ + ".pdf"
        file_path = path / filename
        if file_path.exists() and not overwrite:
            logger.debug(
                f"Datasheet for {m} already exists, skipping download"  # noqa: E501
            )
            continue
        try:
            _download_datasheet(url, file_path)
        except DatasheetDownloadException as e:
            logger.error(f"Failed to download datasheet for {m}: {e}")

        logger.debug(f"Downloaded datasheet for {m}")


class DatasheetDownloadException(Exception):
    pass


def _download_datasheet(url: str, path: Path):
    """
    Download the datasheet of the given module and save it to the given path.
    """
    if not url.endswith(".pdf"):
        raise DatasheetDownloadException(f"Datasheet URL {url} is probably not a PDF")
    if not url.startswith(("http://", "https://")):
        raise DatasheetDownloadException(
            f"Datasheet URL {url} is probably not a valid URL"
        )

    try:
        # TODO probably need something fancier
        user_agent_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"  # noqa: E501
        }
        response = requests.get(url, headers=user_agent_headers)
        response.raise_for_status()
    except requests.RequestException as e:
        raise DatasheetDownloadException(
            f"Failed to download datasheet from {url}: {e}"
        ) from e

    # check if content is pdf
    if not response.content.startswith(b"%PDF"):
        raise DatasheetDownloadException(
            f"Downloaded content is not a PDF: {response.content[:100]}"
        )

    try:
        path.write_bytes(response.content)
    except Exception as e:
        raise DatasheetDownloadException(
            f"Failed to save datasheet to {path}: {e}"
        ) from e
