from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx
import pytest

from ..compression import compare_bytes, sha256_hex
from ..config import FetchConfig
from ..models import ArtifactType, FetchArtifactRecord
from ..storage.manifest_store import LocalManifestStore
from ..storage.object_store import LocalObjectStore

_PREVIEW_PDF_URL_RE = re.compile(r'previewPdfUrl:"([^"]+)"')
_JS_UNICODE_ESCAPE_RE = re.compile(r"\\u([0-9a-fA-F]{4})")


class DatasheetFetchError(RuntimeError):
    pass


@dataclass(frozen=True)
class DatasheetPayload:
    raw_pdf: bytes
    resolved_url: str
    mime: str
    source_meta: dict[str, object]


def _validate_not_redirected_to_lcsc_home(response: httpx.Response) -> None:
    host = response.url.host or ""
    if host.endswith("lcsc.com") and response.url.path == "/":
        raise DatasheetFetchError("Invalid or expired datasheet URL")


def _decode_js_escaped_url(raw_url: str) -> str:
    replaced = raw_url.replace("\\/", "/")
    return _JS_UNICODE_ESCAPE_RE.sub(
        lambda match: chr(int(match.group(1), 16)),
        replaced,
    )


def _extract_embedded_pdf_url(html: str, *, base_url: str) -> str:
    match = _PREVIEW_PDF_URL_RE.search(html)
    if not match:
        raise DatasheetFetchError("Could not find embedded datasheet PDF URL in HTML")
    raw_url = _decode_js_escaped_url(match.group(1)).strip()
    while raw_url.startswith("///"):
        raw_url = raw_url[1:]
    if raw_url.startswith("//"):
        return f"https:{raw_url}"
    return urljoin(base_url, raw_url)


def fetch_datasheet_payload(
    datasheet_url: str,
    *,
    timeout_s: float,
    client: httpx.Client,
) -> DatasheetPayload:
    headers = {"User-Agent": "Wget/1.20.3"}
    response = client.get(
        datasheet_url,
        headers=headers,
        follow_redirects=True,
        timeout=timeout_s,
    )
    response.raise_for_status()
    _validate_not_redirected_to_lcsc_home(response)
    content_type = response.headers.get("content-type", "").lower()

    if "text/html" in content_type:
        pdf_url = _extract_embedded_pdf_url(
            response.text,
            base_url=str(response.url),
        )
        pdf_response = client.get(
            pdf_url,
            headers=headers,
            follow_redirects=True,
            timeout=timeout_s,
        )
        pdf_response.raise_for_status()
        _validate_not_redirected_to_lcsc_home(pdf_response)
        pdf_type = pdf_response.headers.get("content-type", "").lower()
        is_pdf = "application/pdf" in pdf_type or pdf_response.content.startswith(
            b"%PDF"
        )
        if not is_pdf:
            raise DatasheetFetchError(f"Embedded URL did not return PDF: {pdf_type}")
        return DatasheetPayload(
            raw_pdf=pdf_response.content,
            resolved_url=str(pdf_response.url),
            mime="application/pdf",
            source_meta={
                "initial_url": datasheet_url,
                "initial_status_code": response.status_code,
                "initial_content_type": content_type,
                "embedded_pdf_url": pdf_url,
                "final_status_code": pdf_response.status_code,
                "final_content_type": pdf_type,
            },
        )

    if "application/pdf" in content_type or response.content.startswith(b"%PDF"):
        return DatasheetPayload(
            raw_pdf=response.content,
            resolved_url=str(response.url),
            mime="application/pdf",
            source_meta={
                "initial_url": datasheet_url,
                "initial_status_code": response.status_code,
                "initial_content_type": content_type,
            },
        )

    raise DatasheetFetchError(f"Unsupported datasheet content type: {content_type}")


def fetch_store_datasheet_with_roundtrip(
    *,
    lcsc_id: int,
    datasheet_url: str,
    config: FetchConfig,
    object_store: LocalObjectStore,
    manifest_store: LocalManifestStore,
    client: httpx.Client | None = None,
) -> FetchArtifactRecord:
    owns_client = client is None
    http_client = client or httpx.Client()
    try:
        payload = fetch_datasheet_payload(
            datasheet_url,
            timeout_s=config.request_timeout_s,
            client=http_client,
        )
    finally:
        if owns_client:
            http_client.close()

    blob = object_store.put_raw(ArtifactType.DATASHEET_PDF, payload.raw_pdf)
    roundtrip_raw = object_store.get_raw(blob.key)
    compare_ok = compare_bytes(payload.raw_pdf, roundtrip_raw) and (
        sha256_hex(payload.raw_pdf) == sha256_hex(roundtrip_raw)
    )
    if not compare_ok:
        raise DatasheetFetchError("Round-trip compare failed for datasheet payload")

    record = FetchArtifactRecord.now(
        lcsc_id=lcsc_id,
        artifact_type=ArtifactType.DATASHEET_PDF,
        source_url=datasheet_url,
        raw_sha256=blob.raw_sha256,
        raw_size_bytes=blob.raw_size_bytes,
        stored_key=blob.key,
        source_meta=payload.source_meta | {"resolved_url": payload.resolved_url},
        mime=payload.mime,
        compare_ok=compare_ok,
    )
    manifest_store.append(record)
    return record


def test_fetch_store_datasheet_roundtrip_direct_pdf(tmp_path) -> None:
    pdf_bytes = b"%PDF-1.7 test\n"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://example.com/ds.pdf"
        return httpx.Response(
            200,
            headers={"content-type": "application/pdf"},
            content=pdf_bytes,
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    config = FetchConfig.from_env()
    object_store = LocalObjectStore(tmp_path)
    manifest_store = LocalManifestStore(tmp_path)

    record = fetch_store_datasheet_with_roundtrip(
        lcsc_id=2040,
        datasheet_url="https://example.com/ds.pdf",
        config=config,
        object_store=object_store,
        manifest_store=manifest_store,
        client=client,
    )
    client.close()

    assert record.artifact_type == ArtifactType.DATASHEET_PDF
    assert object_store.get_raw(record.stored_key) == pdf_bytes
    assert manifest_store.list_for_lcsc(2040)[0].compare_ok


def test_fetch_store_datasheet_roundtrip_html_wrapper(tmp_path) -> None:
    pdf_url = "https://cdn.example.com/ds.pdf"
    html = (
        '<script>window.__NUXT__={previewPdfUrl:"https:\\/\\/cdn.example.com\\/ds.pdf"};'
        "</script>"
    )
    pdf_bytes = b"%PDF-1.4 wrapped\n"

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://example.com/landing":
            return httpx.Response(200, headers={"content-type": "text/html"}, text=html)
        if str(request.url) == pdf_url:
            return httpx.Response(
                200,
                headers={"content-type": "application/pdf"},
                content=pdf_bytes,
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    config = FetchConfig.from_env()
    object_store = LocalObjectStore(tmp_path)
    manifest_store = LocalManifestStore(tmp_path)

    record = fetch_store_datasheet_with_roundtrip(
        lcsc_id=2289,
        datasheet_url="https://example.com/landing",
        config=config,
        object_store=object_store,
        manifest_store=manifest_store,
        client=client,
    )
    client.close()

    assert record.source_meta["embedded_pdf_url"] == pdf_url
    assert object_store.get_raw(record.stored_key) == pdf_bytes


def test_fetch_store_datasheet_roundtrip_html_wrapper_js_unicode_url(tmp_path) -> None:
    pdf_url = "https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/C21190.pdf"
    html = (
        '<script>window.__NUXT__={previewPdfUrl:"/\\u002F\\u002Fwmsc.lcsc.com'
        '\\u002Fwmsc\\u002Fupload\\u002Ffile\\u002Fpdf\\u002Fv2\\u002FC21190.pdf"};'
        "</script>"
    )
    pdf_bytes = b"%PDF-1.4 js-escaped\n"

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://www.lcsc.com/datasheet/C21190.pdf":
            return httpx.Response(200, headers={"content-type": "text/html"}, text=html)
        if str(request.url) == pdf_url:
            return httpx.Response(
                200,
                headers={"content-type": "application/pdf"},
                content=pdf_bytes,
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    config = FetchConfig.from_env()
    object_store = LocalObjectStore(tmp_path)
    manifest_store = LocalManifestStore(tmp_path)

    record = fetch_store_datasheet_with_roundtrip(
        lcsc_id=21190,
        datasheet_url="https://www.lcsc.com/datasheet/C21190.pdf",
        config=config,
        object_store=object_store,
        manifest_store=manifest_store,
        client=client,
    )
    client.close()

    assert record.source_meta["embedded_pdf_url"] == pdf_url
    assert object_store.get_raw(record.stored_key) == pdf_bytes


def test_fetch_datasheet_payload_rejects_lcsc_home_redirect() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://example.com/expired":
            return httpx.Response(
                302,
                headers={"location": "https://www.lcsc.com/"},
            )
        if str(request.url) == "https://www.lcsc.com/":
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="<html>home</html>",
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    with pytest.raises(DatasheetFetchError, match="Invalid or expired datasheet URL"):
        fetch_datasheet_payload(
            "https://example.com/expired",
            timeout_s=10,
            client=client,
        )
    client.close()


def test_fetch_datasheet_payload_rejects_html_without_embedded_pdf() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="<html><body>no preview url here</body></html>",
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    with pytest.raises(
        DatasheetFetchError,
        match="Could not find embedded datasheet PDF URL in HTML",
    ):
        fetch_datasheet_payload(
            "https://example.com/no-pdf",
            timeout_s=10,
            client=client,
        )
    client.close()


def test_fetch_datasheet_payload_rejects_unsupported_content_type() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            200,
            headers={"content-type": "image/png"},
            content=b"\x89PNG\r\n\x1a\n",
        )

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    with pytest.raises(DatasheetFetchError, match="Unsupported datasheet content type"):
        fetch_datasheet_payload(
            "https://example.com/not-a-datasheet",
            timeout_s=10,
            client=client,
        )
    client.close()
