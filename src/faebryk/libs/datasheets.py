# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import hashlib
import logging
import re
from pathlib import Path

from httpx import HTTPStatusError, RequestError, TimeoutException

from faebryk.libs.http import http_client

logger = logging.getLogger(__name__)

_LCSC_ID_RE = re.compile(r"(C\d{4,10})", re.IGNORECASE)


class DatasheetDownloadException(Exception):
    pass


def normalize_lcsc_id(raw: str | None) -> str | None:
    if not raw:
        return None
    token = raw.strip().upper()
    if not token:
        return None
    if token.startswith("C"):
        number = token[1:]
    else:
        number = token
        token = f"C{token}"
    if not number.isdigit():
        return None
    return token


def extract_lcsc_id_from_url(url: str) -> str | None:
    match = _LCSC_ID_RE.search(url)
    if not match:
        return None
    return normalize_lcsc_id(match.group(1))


def lcsc_wmsc_url(url: str) -> str | None:
    if "lcsc.com" not in url.lower() or "wmsc.lcsc.com" in url.lower():
        return None
    lcsc_id = extract_lcsc_id_from_url(url)
    if not lcsc_id:
        return None
    return f"https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/{lcsc_id}.pdf"


def lcsc_wmsc_url_for_id(lcsc_id: str) -> str | None:
    normalized = normalize_lcsc_id(lcsc_id)
    if not normalized:
        return None
    return f"https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/{normalized}.pdf"


def extract_filename_from_url(url: str) -> str:
    url_filename = Path(url).name

    # If URL doesn't end in .pdf or has no valid filename, create one from URL.
    if not url_filename or not url_filename.endswith(".pdf"):
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        url_filename = f"datasheet_{url_hash}.pdf"

    # Clean up LCSC filenames: remove "lcsc_datasheet_NNNNNNNNNN_" prefix.
    if url_filename.startswith("lcsc_datasheet_"):
        parts = url_filename.split("_", 3)  # Split into max 4 parts
        if len(parts) >= 4:
            # ["lcsc", "datasheet", "date", "MFR-PART_CXXXXX.pdf"]
            url_filename = parts[3]

    return url_filename


def datasheet_cache_dir(build_path: Path) -> Path:
    return build_path / "cache" / "parts" / "datasheets"


def datasheet_cache_path(build_path: Path, lcsc_id: str) -> Path | None:
    normalized = normalize_lcsc_id(lcsc_id)
    if not normalized:
        return None
    return datasheet_cache_dir(build_path) / f"{normalized}.pdf"


def download_datasheet(url: str, path: Path, timeout_s: int = 15) -> None:
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
            response = client.get(url, timeout=timeout_s, follow_redirects=False)

            # Handle redirects explicitly (httpx doesn't treat 3xx as errors).
            if response.status_code in {301, 302, 303, 307, 308}:
                # Some LCSC datasheets are moved; map to the stable wmsc URL.
                if redirected_url := lcsc_wmsc_url(url):
                    logger.info(f"LCSC redirect fallback: {url} -> {redirected_url}")
                    download_datasheet(redirected_url, path, timeout_s=timeout_s)
                    return

                # Otherwise, follow the Location header if present.
                location = response.headers.get("location")
                if location:
                    download_datasheet(location, path, timeout_s=timeout_s)
                    return

            response.raise_for_status()
    except HTTPStatusError as exc:
        raise DatasheetDownloadException(
            f"HTTP error downloading datasheet from {url}: {exc}"
        ) from exc
    except TimeoutException as exc:
        raise DatasheetDownloadException(
            f"Timed out (>{timeout_s}s) downloading datasheet from {url}: {exc}"
        ) from exc
    except RequestError as exc:
        raise DatasheetDownloadException(
            f"Failed to download datasheet from {url}: {exc}"
        ) from exc

    # Do not trust content-type/suffix alone for datasheet hosts.
    if not response.content.startswith(b"%PDF"):
        if redirected_url := lcsc_wmsc_url(url):
            logger.info(f"LCSC non-PDF fallback: {url} -> {redirected_url}")
            download_datasheet(redirected_url, path, timeout_s=timeout_s)
            return
        raise DatasheetDownloadException(
            f"Downloaded content is not a PDF: {response.content[:100]}"
        )

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)
    except Exception as exc:
        raise DatasheetDownloadException(
            f"Failed to save datasheet to {path}: {exc}"
        ) from exc
