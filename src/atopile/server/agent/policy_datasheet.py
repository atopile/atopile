"""Datasheet resolution and extraction helpers for agent policy."""

from __future__ import annotations

import hashlib
import html
import io
import re
import time
from pathlib import Path
from typing import Callable, Literal
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from faebryk.libs.datasheets import lcsc_wmsc_url

_MAX_DATASHEET_BYTES = 30_000_000
_MAX_DATASHEET_PAGES = 25
_MAX_DATASHEET_CHARS = 50_000
_MIN_DATASHEET_CHARS = 500
_MAX_DATASHEET_SNIPPETS = 8
_DATASHEET_FETCH_TIMEOUT_S = 45
_DATASHEET_FETCH_RETRIES = 2


def read_datasheet_file(
    project_root: Path,
    *,
    path: str | None = None,
    url: str | None = None,
    resolve_scoped_path: Callable[[Path, str], Path],
    scope_error_cls: type[Exception],
) -> tuple[bytes, dict[str, object]]:
    """Resolve datasheet bytes from a local file or remote URL."""
    sources = [bool(path and str(path).strip()), bool(url and str(url).strip())]
    if sum(1 for source in sources if source) != 1:
        raise scope_error_cls("Provide exactly one datasheet source: path or url")

    if path and str(path).strip():
        raw_bytes, source_value, content_type = _read_datasheet_bytes_from_path(
            project_root,
            str(path),
            resolve_scoped_path=resolve_scoped_path,
            scope_error_cls=scope_error_cls,
        )
        source_kind: Literal["path", "url"] = "path"
    else:
        raw_bytes, source_value, content_type = _read_datasheet_bytes_from_url(
            str(url or ""),
            scope_error_cls=scope_error_cls,
        )
        source_kind = "url"

    if not raw_bytes:
        raise scope_error_cls("Datasheet source returned empty content.")

    data_format = _detect_datasheet_format(
        source_value=source_value,
        content_type=content_type,
        raw_bytes=raw_bytes,
    )
    if data_format != "pdf":
        details: list[str] = [f"detected_format={data_format}"]
        if content_type:
            details.append(f"content_type={content_type}")
        raise scope_error_cls(
            "Datasheet source is not a valid PDF "
            f"({'; '.join(details)}). "
            "This often means the URL returned HTML instead of the file."
        )

    filename = _guess_datasheet_filename(
        source_value=source_value,
        source_kind=source_kind,
        raw_bytes=raw_bytes,
    )
    sha256 = hashlib.sha256(raw_bytes).hexdigest()
    metadata: dict[str, object] = {
        "source_kind": source_kind,
        "source": source_value,
        "format": "pdf",
        "content_type": content_type or "application/pdf",
        "filename": filename,
        "sha256": sha256,
        "size_bytes": len(raw_bytes),
    }
    return raw_bytes, metadata


def read_datasheet_content(
    project_root: Path,
    *,
    path: str | None = None,
    url: str | None = None,
    start_page: int = 1,
    max_pages: int = 4,
    query: str | None = None,
    max_chars: int = 16_000,
    resolve_scoped_path: Callable[[Path, str], Path],
    scope_error_cls: type[Exception],
) -> dict:
    """Read datasheet text from a local file or remote URL."""
    if start_page < 1:
        raise scope_error_cls("start_page must be >= 1")
    if max_pages < 1 or max_pages > _MAX_DATASHEET_PAGES:
        raise scope_error_cls(f"max_pages must be between 1 and {_MAX_DATASHEET_PAGES}")
    if max_chars < _MIN_DATASHEET_CHARS or max_chars > _MAX_DATASHEET_CHARS:
        raise scope_error_cls(
            "max_chars must be between "
            f"{_MIN_DATASHEET_CHARS} and {_MAX_DATASHEET_CHARS}"
        )

    sources = [bool(path and str(path).strip()), bool(url and str(url).strip())]
    if sum(1 for source in sources if source) != 1:
        raise scope_error_cls("Provide exactly one datasheet source: path or url")

    if path and str(path).strip():
        raw_bytes, source_value, content_type = _read_datasheet_bytes_from_path(
            project_root,
            str(path),
            resolve_scoped_path=resolve_scoped_path,
            scope_error_cls=scope_error_cls,
        )
        source_kind = "path"
    else:
        raw_bytes, source_value, content_type = _read_datasheet_bytes_from_url(
            str(url or ""),
            scope_error_cls=scope_error_cls,
        )
        source_kind = "url"

    data_format = _detect_datasheet_format(
        source_value=source_value,
        content_type=content_type,
        raw_bytes=raw_bytes,
    )

    if data_format == "pdf":
        extracted = _extract_pdf_text(
            raw_bytes=raw_bytes,
            start_page=start_page,
            max_pages=max_pages,
            scope_error_cls=scope_error_cls,
        )
        snippets = _extract_query_snippets(
            query=query,
            page_texts=extracted["page_texts"],
        )
        combined_text = extracted["content"]
        total_pages = extracted["total_pages"]
        page_range = {
            "start": extracted["start_page"],
            "end": extracted["end_page"],
        }
    else:
        decoded = _decode_datasheet_bytes(raw_bytes, scope_error_cls=scope_error_cls)
        if data_format == "html":
            decoded = _strip_html(decoded)
        combined_text = _normalize_newlines(decoded).strip()
        snippets = _extract_query_snippets(
            query=query,
            page_texts=[(None, combined_text)],
        )
        total_pages = None
        page_range = None

    truncated_content, truncated = _truncate_chars(combined_text, max_chars)
    query_text = query.strip() if isinstance(query, str) else ""
    return {
        "source_kind": source_kind,
        "source": source_value,
        "format": data_format,
        "content_type": content_type,
        "content": truncated_content,
        "content_chars": len(truncated_content),
        "truncated": truncated,
        "total_pages": total_pages,
        "page_range": page_range,
        "query": query_text or None,
        "query_matches": snippets,
    }


def _read_datasheet_bytes_from_path(
    project_root: Path,
    path: str,
    *,
    resolve_scoped_path: Callable[[Path, str], Path],
    scope_error_cls: type[Exception],
) -> tuple[bytes, str, str | None]:
    file_path = resolve_scoped_path(project_root, path)
    if not file_path.exists() or not file_path.is_file():
        raise scope_error_cls(f"Datasheet file does not exist: {path}")

    size = file_path.stat().st_size
    if size > _MAX_DATASHEET_BYTES:
        raise scope_error_cls(
            f"Datasheet too large ({size} bytes > {_MAX_DATASHEET_BYTES} bytes)"
        )

    raw = file_path.read_bytes()
    relative = str(file_path.relative_to(project_root))
    content_type = "application/pdf" if file_path.suffix.lower() == ".pdf" else None
    return raw, relative, content_type


def _read_datasheet_bytes_from_url(
    url: str,
    *,
    scope_error_cls: type[Exception],
) -> tuple[bytes, str, str | None]:
    cleaned = url.strip()
    parsed = urllib_parse.urlparse(cleaned)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise scope_error_cls("datasheet url must start with http:// or https://")
    if not parsed.netloc:
        raise scope_error_cls("datasheet url is missing host")

    candidate_urls = [cleaned]
    if wmsc_url := lcsc_wmsc_url(cleaned):
        if wmsc_url not in candidate_urls:
            candidate_urls.append(wmsc_url)

    last_error: Exception | None = None
    for attempt in range(_DATASHEET_FETCH_RETRIES):
        for candidate_url in list(candidate_urls):
            request = urllib_request.Request(
                candidate_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/50.0.2661.102 Safari/537.36"
                    )
                },
            )
            try:
                with urllib_request.urlopen(
                    request, timeout=_DATASHEET_FETCH_TIMEOUT_S
                ) as response:
                    stream = response
                    raw = _read_stream_with_limit(
                        stream,
                        _MAX_DATASHEET_BYTES,
                        scope_error_cls=scope_error_cls,
                    )
                    content_type = response.headers.get("Content-Type")
                    if isinstance(content_type, str):
                        content_type = content_type.split(";", 1)[0].strip().lower()
                    else:
                        content_type = None
                    final_url = getattr(response, "geturl", lambda: candidate_url)()
                    if not isinstance(final_url, str) or not final_url.strip():
                        final_url = candidate_url
            except (
                urllib_error.URLError,
                TimeoutError,
                OSError,
            ) as exc:
                last_error = exc
                continue

            if _looks_like_html_content(raw):
                fallback = lcsc_wmsc_url(final_url)
                if fallback is None:
                    fallback = lcsc_wmsc_url(candidate_url)
                if fallback:
                    if fallback not in candidate_urls:
                        candidate_urls.append(fallback)
                    if candidate_url != fallback:
                        continue
            return raw, final_url, content_type

        if attempt < _DATASHEET_FETCH_RETRIES - 1:
            time.sleep(0.2)

    detail = f"{type(last_error).__name__}: {last_error}" if last_error else "unknown"
    raise scope_error_cls(f"Failed to fetch datasheet url: {cleaned} ({detail})")


def _read_stream_with_limit(
    stream: io.BufferedIOBase,
    max_bytes: int,
    *,
    scope_error_cls: type[Exception],
) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = stream.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise scope_error_cls(f"Datasheet exceeds max size limit ({max_bytes} bytes)")
        chunks.append(chunk)
    return b"".join(chunks)


def _looks_like_html_content(raw: bytes) -> bool:
    head = raw[:4096].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html")


def _guess_datasheet_filename(
    *,
    source_value: str,
    source_kind: Literal["path", "url"],
    raw_bytes: bytes,
) -> str:
    if source_kind == "path":
        candidate = Path(source_value).name
    else:
        parsed = urllib_parse.urlparse(source_value)
        candidate = Path(parsed.path).name

    candidate = candidate.strip()
    if not candidate:
        candidate = f"datasheet-{hashlib.sha256(raw_bytes).hexdigest()[:10]}.pdf"

    candidate = re.sub(r"[^A-Za-z0-9._-]+", "_", candidate).strip("._")
    if not candidate:
        candidate = f"datasheet-{hashlib.sha256(raw_bytes).hexdigest()[:10]}.pdf"
    if not candidate.lower().endswith(".pdf"):
        candidate = f"{candidate}.pdf"

    return candidate[:140]


def _detect_datasheet_format(
    *,
    source_value: str,
    content_type: str | None,
    raw_bytes: bytes,
) -> Literal["pdf", "html", "text"]:
    lowered_source = source_value.lower()
    lowered_type = (content_type or "").lower()
    head = raw_bytes[:4096].lstrip().lower()

    if b"%pdf-" in raw_bytes[:1024].lower():
        return "pdf"
    if head.startswith(b"<!doctype html") or head.startswith(b"<html"):
        return "html"

    if lowered_type.startswith("application/pdf") or lowered_source.endswith(".pdf"):
        return "text"

    if "html" in lowered_type:
        return "html"
    if lowered_source.endswith(".html") or lowered_source.endswith(".htm"):
        return "html"

    return "text"


def _extract_pdf_text(
    *,
    raw_bytes: bytes,
    start_page: int,
    max_pages: int,
    scope_error_cls: type[Exception],
) -> dict[str, object]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise scope_error_cls(
            "PDF extraction requires pypdf. Install dependency and retry."
        ) from exc

    try:
        reader = PdfReader(io.BytesIO(raw_bytes))
    except Exception as exc:
        raise scope_error_cls(f"Failed to parse PDF datasheet: {exc}") from exc

    total_pages = len(reader.pages)
    if total_pages == 0:
        raise scope_error_cls("PDF datasheet has no pages")
    if start_page > total_pages:
        raise scope_error_cls(
            f"start_page {start_page} exceeds total pages ({total_pages})"
        )

    end_page = min(total_pages, start_page + max_pages - 1)
    page_texts: list[tuple[int | None, str]] = []
    content_sections: list[str] = []
    for page_number in range(start_page, end_page + 1):
        page = reader.pages[page_number - 1]
        text = page.extract_text() or ""
        normalized = _normalize_newlines(text).strip()
        page_texts.append((page_number, normalized))
        if normalized:
            content_sections.append(f"[Page {page_number}]\n{normalized}")
        else:
            content_sections.append(f"[Page {page_number}]\n<no extractable text>")

    return {
        "content": "\n\n".join(content_sections).strip(),
        "total_pages": total_pages,
        "start_page": start_page,
        "end_page": end_page,
        "page_texts": page_texts,
    }


def _decode_datasheet_bytes(
    raw_bytes: bytes,
    *,
    scope_error_cls: type[Exception],
) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise scope_error_cls("Datasheet content could not be decoded as text")


def _strip_html(raw_html: str) -> str:
    without_script = re.sub(
        r"(?is)<(script|style).*?>.*?</\1>",
        " ",
        raw_html,
    )
    without_tags = re.sub(r"(?s)<[^>]+>", " ", without_script)
    unescaped = html.unescape(without_tags)
    normalized = _normalize_newlines(unescaped)
    lines = [line.strip() for line in normalized.splitlines()]
    return "\n".join(line for line in lines if line)


def _extract_query_snippets(
    *,
    query: str | None,
    page_texts: list[tuple[int | None, str]],
) -> list[dict[str, object]]:
    needle = query.strip().lower() if isinstance(query, str) else ""
    if not needle:
        return []

    snippets: list[dict[str, object]] = []
    for page, text in page_texts:
        haystack = text.lower()
        offset = 0
        while len(snippets) < _MAX_DATASHEET_SNIPPETS:
            index = haystack.find(needle, offset)
            if index < 0:
                break
            start = max(0, index - 100)
            end = min(len(text), index + len(needle) + 140)
            snippet_text = text[start:end].strip()
            if snippet_text:
                snippets.append(
                    {
                        "page": page,
                        "snippet": snippet_text,
                    }
                )
            offset = index + len(needle)
        if len(snippets) >= _MAX_DATASHEET_SNIPPETS:
            break

    return snippets


def _truncate_chars(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return text[: max_chars - 3].rstrip() + "...", True


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")
