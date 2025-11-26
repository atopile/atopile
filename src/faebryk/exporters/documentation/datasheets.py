# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from pathlib import Path

from httpx import RequestError

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.http import http_client

logger = logging.getLogger(__name__)


def export_datasheets(
    app: fabll.Node,
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
    for m in fabll.Traits.get_implementors(F.has_datasheet.bind_typegraph(tg=app.tg)):
        url = m.get_datasheet()
        if not url:
            logger.warning(f"Missing datasheet URL for {m.get_name()}")
            continue
        parent_type_name = m.get_parent_with_trait(fabll.is_module)[0].get_type_name()
        if parent_type_name is None:
            logger.warning(f"Missing parent name for {m.get_name()}")
            continue
        filename = parent_type_name + ".pdf"
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
        user_agent_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
        }
        with http_client(headers=user_agent_headers) as client:
            response = client.get(url)
            response.raise_for_status()
    except RequestError as e:
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


def test_download_datasheet(caplog):
    URL = "https://www.ti.com/lit/ds/symlink/lm555.pdf"
    DEFAULT_PATH = Path("build/documentation/datasheets/")

    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=graph.GraphView.create())

    class App(fabll.Node):
        class ModuleWithDatasheet(fabll.Node):
            _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
            datasheet = fabll.Traits.MakeEdge(F.has_datasheet.MakeChild(datasheet=URL))

        module_with_datasheet = ModuleWithDatasheet.MakeChild()

    app = App.bind_typegraph(tg=tg).create_instance(g=g)

    assert app.module_with_datasheet.get().has_trait(F.has_datasheet)

    export_datasheets(app, path=DEFAULT_PATH)

    assert (DEFAULT_PATH / "ModuleWithDatasheet.pdf").exists()
