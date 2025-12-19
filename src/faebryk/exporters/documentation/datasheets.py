# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import re
from pathlib import Path

from httpx import HTTPStatusError, RequestError

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.http import http_client

logger = logging.getLogger(__name__)

# Maximum characters for the joined module names in the filename
# (excluding .pdf extension)
MAX_FILE_NAME_CHARACTERS = 100


class DatasheetDownloadException(Exception):
    pass


def export_datasheets(
    app: fabll.Node,
    path: Path = Path("build/documentation/datasheets"),
    overwrite: bool = False,
):
    """
    Export all datasheets of all modules (that have a datasheet defined)
    of the given application.

    Downloads each unique datasheet URL once, naming the file with all
    module names that share that URL joined by underscores.
    """
    # Create directories if they don't exist
    path.mkdir(parents=True, exist_ok=True)

    # First pass: collect all URLs and their associated module names
    url_to_modules: dict[str, list[str]] = {}
    logger.info(f"Exporting datasheets to: {path}")
    for m in fabll.Traits.get_implementor_objects(
        F.has_datasheet.bind_typegraph(tg=app.tg)
    ):
        datasheet_trait = m.try_get_trait(F.has_datasheet)
        if datasheet_trait is None:
            logger.warning(f"Missing datasheet trait for {m.get_name()}")
            continue
        url = datasheet_trait.get_datasheet()
        if not url:
            logger.warning(f"Missing datasheet URL for {m.get_name()}")
            continue
        module_name = m.get_name()
        if url not in url_to_modules:
            url_to_modules[url] = []
        url_to_modules[url].append(module_name)

    # Second pass: download each unique URL with combined module names as filename
    for url, module_names in url_to_modules.items():
        base_name = "_".join(sorted(module_names))
        if len(base_name) > MAX_FILE_NAME_CHARACTERS:
            base_name = base_name[: MAX_FILE_NAME_CHARACTERS - 2] + "__"
        filename = base_name + ".pdf"
        file_path = path / filename
        if file_path.exists() and not overwrite:
            logger.debug(
                f"Datasheet for {module_names} already exists, skipping download"
            )
            continue
        try:
            _download_datasheet(url, file_path)
        except DatasheetDownloadException as e:
            logger.error(f"Failed to download datasheet for {module_names}: {e}")
            continue
        logger.debug(f"Downloaded datasheet for {module_names}")


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
    except HTTPStatusError as e:
        # Some LCSC datasheets are moved, follow the redirect manually
        if e.response.status_code == 301:
            if "lcsc.com" in url:
                # get the lcsc id from the url
                lcsc_id_regex = r"_(C\d{4,8})"
                match = re.search(lcsc_id_regex, url)
                if match:
                    lcsc_id = match.group(1)
                    redirected_url = (
                        f"https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/{lcsc_id}.pdf"
                    )
                    logger.warning(f"LCSC 301 redirect: {url} -> {redirected_url}")
                    _download_datasheet(redirected_url, path)
                    return  # Exit after successful recursive download
        # Re-raise if we couldn't handle the redirect
        raise DatasheetDownloadException(
            f"HTTP error downloading datasheet from {url}: {e}"
        ) from e
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


def _create_app_with_datasheet(url: str):
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=graph.GraphView.create())

    class ModuleWithDatasheet(fabll.Node):
        _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())
        datasheet = fabll.Traits.MakeEdge(F.has_datasheet.MakeChild(datasheet=url))

    class App(fabll.Node):
        modules_with_datasheet = [ModuleWithDatasheet.MakeChild() for _ in range(2)]

    return App.bind_typegraph(tg=tg).create_instance(g=g)


def test_download_datasheet(caplog, tmp_path):
    URL = "https://www.ti.com/lit/ds/symlink/lm555.pdf"
    DEFAULT_PATH = tmp_path / "datasheets"

    app = _create_app_with_datasheet(URL)

    datasheet_a = app.modules_with_datasheet[0].get().try_get_trait(F.has_datasheet)
    datasheet_b = app.modules_with_datasheet[1].get().try_get_trait(F.has_datasheet)
    assert datasheet_a is not None
    assert datasheet_b is not None

    assert datasheet_a.get_datasheet() == URL
    assert datasheet_b.get_datasheet() == URL

    export_datasheets(app, path=DEFAULT_PATH)

    # check that exactly one datasheet file was downloaded
    # (both modules share the same URL, so deduplication should result in one file)
    # filename should be both module names joined with underscore
    pdf_files = list(DEFAULT_PATH.glob("*.pdf"))
    assert len(pdf_files) == 1, f"Expected 1 PDF, got: {pdf_files}"
    expected_name = "modules_with_datasheet[0]_modules_with_datasheet[1].pdf"
    assert (DEFAULT_PATH / expected_name).exists(), (
        f"Expected {expected_name}, got: {[f.name for f in pdf_files]}"
    )


def test_download_datasheet_failure(caplog, tmp_path):
    URL = "fake_url.pdf"
    DEFAULT_PATH = tmp_path / "datasheets"

    app = _create_app_with_datasheet(URL)

    with caplog.at_level(logging.ERROR):
        export_datasheets(app, path=DEFAULT_PATH)

    # check that no datasheet files were downloaded due to the invalid URL
    pdf_files = list(DEFAULT_PATH.glob("*.pdf"))
    assert len(pdf_files) == 0, f"Expected no PDFs, got: {pdf_files}"
    # verify that the failure was logged with DatasheetDownloadException
    # "fake_url.pdf" fails the URL protocol check
    assert any(
        "is probably not a valid URL" in record.message for record in caplog.records
    ), (
        f"Expected DatasheetDownloadException to be logged, "
        f"got: {[r.message for r in caplog.records]}"
    )
