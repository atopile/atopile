"""Agent scope and file-access policy helpers."""

from __future__ import annotations

import difflib
import hashlib
import html
import io
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from atopile.dataclasses import AppContext

# Keep context focused on source/config/docs files.
_ALLOWED_EXTENSIONS = {
    ".ato",
    ".py",
    ".pyi",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".css",
    ".sh",
}

_EXCLUDED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "__pycache__",
    ".ato",
    "build",
    "node_modules",
    "dist",
    "coverage",
}

_MAX_CONTEXT_FILE_BYTES = 180_000
_MAX_WRITE_FILE_BYTES = 600_000
_MAX_UI_DIFF_BYTES = 220_000
_MAX_DATASHEET_BYTES = 30_000_000
_HASH_HEX_CHARS = 4
_HASHLINE_CONTEXT_LINES = 2
_MAX_DATASHEET_PAGES = 25
_MAX_DATASHEET_CHARS = 50_000
_MIN_DATASHEET_CHARS = 500
_MAX_DATASHEET_SNIPPETS = 8
_DATASHEET_FETCH_TIMEOUT_S = 45
_DATASHEET_FETCH_RETRIES = 2

_ANCHOR_RE = re.compile(r"^(\d+)\s*:\s*([0-9A-Za-z]{1,16})$")
_ANCHOR_PREFIX_RE = re.compile(r"^(\d+)\s*:\s*([0-9A-Za-z]{1,16})")
_LCSC_ID_RE = re.compile(r"(C\d{4,10})", re.IGNORECASE)


@dataclass(frozen=True)
class MatchLine:
    path: str
    line: int
    text: str


@dataclass(frozen=True)
class LineAnchor:
    line: int
    hash: str


@dataclass(frozen=True)
class HashlineMismatch:
    line: int
    expected: str
    actual: str


@dataclass(frozen=True)
class SetLineOperation:
    index: int
    anchor: LineAnchor
    new_text: str


@dataclass(frozen=True)
class ReplaceLinesOperation:
    index: int
    start_anchor: LineAnchor
    end_anchor: LineAnchor
    new_text: str


@dataclass(frozen=True)
class InsertAfterOperation:
    index: int
    anchor: LineAnchor
    text: str


EditOperation = SetLineOperation | ReplaceLinesOperation | InsertAfterOperation


class ScopeError(ValueError):
    """Raised when an agent tool attempts to access out-of-scope data."""


class HashlineMismatchError(ScopeError):
    """Raised when hashline anchors are stale for the current file content."""

    def __init__(self, mismatches: list[HashlineMismatch], file_lines: list[str]):
        self.mismatches = mismatches
        self.file_lines = file_lines
        self.remaps = {
            f"{mismatch.line}:{mismatch.expected}": f"{mismatch.line}:{mismatch.actual}"
            for mismatch in mismatches
        }
        super().__init__(_format_mismatch_error(mismatches, file_lines))


def resolve_project_root(project_root: str, ctx: AppContext) -> Path:
    root = Path(project_root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ScopeError(f"Project root does not exist: {project_root}")

    if ctx.workspace_paths:
        allowed = [p.expanduser().resolve() for p in ctx.workspace_paths]
        if not any(root.is_relative_to(ws) or root == ws for ws in allowed):
            raise ScopeError(
                "Project root is outside the current workspace scope"
            )

    ato_yaml = root / "ato.yaml"
    if not ato_yaml.exists():
        raise ScopeError(f"No ato.yaml found in project root: {project_root}")

    return root


def resolve_scoped_path(project_root: Path, path: str) -> Path:
    raw = Path(path).expanduser()
    if raw.is_absolute():
        candidate = raw.resolve()
    else:
        candidate = (project_root / raw).resolve()

    if not candidate.is_relative_to(project_root):
        raise ScopeError(f"Path is outside project scope: {path}")

    return candidate


def _package_path_aliases(path: str) -> list[str]:
    """Return compatible package path aliases for historical layouts."""
    raw = Path(path)
    parts = raw.parts
    aliases: list[str] = []

    if len(parts) >= 3 and parts[0] == ".ato" and parts[1] in {"deps", "packages"}:
        aliases.append(str(Path(".ato", "modules", *parts[2:])))

    # Let callers pass package-relative paths directly.
    if parts and parts[0] != ".ato":
        aliases.append(str(Path(".ato", "modules", *parts)))

    deduped: list[str] = []
    for alias in aliases:
        if alias != path and alias not in deduped:
            deduped.append(alias)
    return deduped


def _resolve_readable_file_path(
    project_root: Path,
    path: str,
) -> tuple[Path, str]:
    """Resolve a readable in-scope file path with package-path compatibility."""
    candidates = [path, *_package_path_aliases(path)]
    resolved_attempts: list[tuple[str, Path]] = []
    for candidate_path in candidates:
        candidate = resolve_scoped_path(project_root, candidate_path)
        resolved_attempts.append((candidate_path, candidate))
        if candidate.exists() and candidate.is_file():
            return candidate, candidate_path

    # If the parent folder exists and contains one .ato file, treat that as
    # the package entry file. This handles stale guesses like `sht45.ato` vs
    # `sensirion-sht45.ato`.
    for candidate_path, candidate in resolved_attempts:
        parent = candidate.parent
        if candidate.suffix.lower() != ".ato":
            continue
        if not parent.exists() or not parent.is_dir():
            continue
        ato_files = sorted(p for p in parent.glob("*.ato") if p.is_file())
        if len(ato_files) == 1:
            return ato_files[0], candidate_path

    suggestion_candidates: list[str] = []
    for candidate_path, candidate in resolved_attempts:
        if candidate_path != path:
            suggestion_candidates.append(candidate_path)

        parent = candidate.parent
        if parent.exists() and parent.is_dir():
            for ato_file in sorted(parent.glob("*.ato"))[:3]:
                if not ato_file.is_file():
                    continue
                rel = str(ato_file.relative_to(project_root))
                suggestion_candidates.append(rel)

    seen: set[str] = set()
    suggestions: list[str] = []
    for suggestion in suggestion_candidates:
        if suggestion in seen:
            continue
        seen.add(suggestion)
        suggestions.append(suggestion)

    if suggestions:
        hint = ", ".join(suggestions[:4])
        raise ScopeError(f"File does not exist: {path}. Try: {hint}")
    raise ScopeError(f"File does not exist: {path}")


def _is_excluded(path: Path, project_root: Path) -> bool:
    try:
        rel = path.relative_to(project_root)
    except ValueError:
        return True

    for part in rel.parts[:-1]:
        if part in _EXCLUDED_DIR_NAMES:
            return True
    return False


def is_context_file(path: Path, project_root: Path) -> bool:
    if _is_excluded(path, project_root):
        return False
    if not path.is_file():
        return False
    if path.suffix.lower() not in _ALLOWED_EXTENSIONS:
        return False
    return path.stat().st_size <= _MAX_CONTEXT_FILE_BYTES


def list_context_files(project_root: Path, limit: int = 300) -> list[str]:
    files: list[str] = []
    for path in project_root.rglob("*"):
        if len(files) >= limit:
            break
        if not is_context_file(path, project_root):
            continue
        files.append(str(path.relative_to(project_root)))
    files.sort()
    return files


def compute_line_hash(line_number: int, line_text: str) -> str:
    """Compute a short hash for a line after whitespace normalization."""
    _ = line_number  # reserved for future hash variants
    normalized = re.sub(r"\s+", "", line_text.rstrip("\r"))
    digest = hashlib.blake2b(normalized.encode("utf-8"), digest_size=2).hexdigest()
    return digest[:_HASH_HEX_CHARS]


def format_hashline_content(lines: list[str], start_line: int = 1) -> str:
    """Return lines encoded as LINE:HASH|CONTENT."""
    if start_line < 1:
        raise ScopeError("start_line must be >= 1")

    return "\n".join(
        f"{line_no}:{compute_line_hash(line_no, line)}|{line}"
        for line_no, line in enumerate(lines, start=start_line)
    )


def parse_line_anchor(raw_anchor: str) -> LineAnchor:
    """Parse a line anchor of the form LINE:HASH, tolerating copied suffixes."""
    if not isinstance(raw_anchor, str):
        raise ScopeError("Anchor must be a string")

    cleaned = raw_anchor.strip()
    if not cleaned:
        raise ScopeError("Anchor must not be empty")

    # If copied from read output, discard source text after '|'.
    cleaned = cleaned.split("|", 1)[0].strip()
    # Also tolerate older copied forms with two spaces before source text.
    cleaned = cleaned.split("  ", 1)[0].strip()

    match = _ANCHOR_RE.match(cleaned) or _ANCHOR_PREFIX_RE.match(cleaned)
    if not match:
        expected = "Expected LINE:HASH (for example '12:1a2b')."
        raise ScopeError(
            f"Invalid anchor '{raw_anchor}'. {expected}"
        )

    line = int(match.group(1))
    if line < 1:
        raise ScopeError(f"Anchor line must be >= 1, got {line}")

    return LineAnchor(line=line, hash=match.group(2).lower())


def read_file_chunk(
    project_root: Path,
    path: str,
    *,
    start_line: int = 1,
    max_lines: int = 200,
) -> dict:
    if start_line < 1:
        raise ScopeError("start_line must be >= 1")
    if max_lines < 1:
        raise ScopeError("max_lines must be >= 1")

    file_path, resolved_input = _resolve_readable_file_path(project_root, path)

    data = file_path.read_text(encoding="utf-8")
    lines = _normalize_newlines(data).splitlines()
    start_idx = start_line - 1
    end_idx = min(len(lines), start_idx + max_lines)

    chunk_lines = lines[start_idx:end_idx]
    chunk = format_hashline_content(chunk_lines, start_line=start_line)
    response: dict[str, str | int] = {
        "path": str(file_path.relative_to(project_root)),
        "start_line": start_line,
        "end_line": end_idx,
        "total_lines": len(lines),
        "content": chunk,
    }
    if resolved_input != path:
        response["resolved_from"] = resolved_input
    return response


def read_datasheet_file(
    project_root: Path,
    *,
    path: str | None = None,
    url: str | None = None,
) -> tuple[bytes, dict[str, object]]:
    """Resolve datasheet bytes from a local file or remote URL."""
    sources = [bool(path and str(path).strip()), bool(url and str(url).strip())]
    if sum(1 for source in sources if source) != 1:
        raise ScopeError("Provide exactly one datasheet source: path or url")

    if path and str(path).strip():
        raw_bytes, source_value, content_type = _read_datasheet_bytes_from_path(
            project_root, str(path)
        )
        source_kind: Literal["path", "url"] = "path"
    else:
        raw_bytes, source_value, content_type = _read_datasheet_bytes_from_url(
            str(url or "")
        )
        source_kind = "url"

    if not raw_bytes:
        raise ScopeError("Datasheet source returned empty content.")

    data_format = _detect_datasheet_format(
        source_value=source_value,
        content_type=content_type,
        raw_bytes=raw_bytes,
    )
    if data_format != "pdf":
        details: list[str] = [f"detected_format={data_format}"]
        if content_type:
            details.append(f"content_type={content_type}")
        raise ScopeError(
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
) -> dict:
    """Read datasheet text from a local file or remote URL."""
    if start_page < 1:
        raise ScopeError("start_page must be >= 1")
    if max_pages < 1 or max_pages > _MAX_DATASHEET_PAGES:
        raise ScopeError(f"max_pages must be between 1 and {_MAX_DATASHEET_PAGES}")
    if max_chars < _MIN_DATASHEET_CHARS or max_chars > _MAX_DATASHEET_CHARS:
        raise ScopeError(
            "max_chars must be between "
            f"{_MIN_DATASHEET_CHARS} and {_MAX_DATASHEET_CHARS}"
        )

    sources = [bool(path and str(path).strip()), bool(url and str(url).strip())]
    if sum(1 for source in sources if source) != 1:
        raise ScopeError("Provide exactly one datasheet source: path or url")

    if path and str(path).strip():
        raw_bytes, source_value, content_type = _read_datasheet_bytes_from_path(
            project_root, str(path)
        )
        source_kind = "path"
    else:
        raw_bytes, source_value, content_type = _read_datasheet_bytes_from_url(
            str(url or "")
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
        decoded = _decode_datasheet_bytes(raw_bytes)
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


def write_file(project_root: Path, path: str, content: str) -> dict:
    file_path = resolve_scoped_path(project_root, path)
    if len(content.encode("utf-8")) > _MAX_WRITE_FILE_BYTES:
        raise ScopeError("Refusing to write very large file content")

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")

    return {
        "path": str(file_path.relative_to(project_root)),
        "bytes": len(content.encode("utf-8")),
    }


def _read_datasheet_bytes_from_path(
    project_root: Path,
    path: str,
) -> tuple[bytes, str, str | None]:
    file_path = resolve_scoped_path(project_root, path)
    if not file_path.exists() or not file_path.is_file():
        raise ScopeError(f"Datasheet file does not exist: {path}")

    size = file_path.stat().st_size
    if size > _MAX_DATASHEET_BYTES:
        raise ScopeError(
            f"Datasheet too large ({size} bytes > {_MAX_DATASHEET_BYTES} bytes)"
        )

    raw = file_path.read_bytes()
    relative = str(file_path.relative_to(project_root))
    content_type = "application/pdf" if file_path.suffix.lower() == ".pdf" else None
    return raw, relative, content_type


def _read_datasheet_bytes_from_url(url: str) -> tuple[bytes, str, str | None]:
    cleaned = url.strip()
    parsed = urllib_parse.urlparse(cleaned)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ScopeError("datasheet url must start with http:// or https://")
    if not parsed.netloc:
        raise ScopeError("datasheet url is missing host")

    candidate_urls = [cleaned]
    if wmsc_url := _lcsc_wmsc_fallback_url(cleaned):
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
                    raw = _read_stream_with_limit(stream, _MAX_DATASHEET_BYTES)
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
                fallback = _lcsc_wmsc_fallback_url(final_url)
                if fallback is None:
                    fallback = _lcsc_wmsc_fallback_url(candidate_url)
                if fallback:
                    if fallback not in candidate_urls:
                        candidate_urls.append(fallback)
                    if candidate_url != fallback:
                        continue
            return raw, final_url, content_type

        # brief backoff before final retry
        if attempt < _DATASHEET_FETCH_RETRIES - 1:
            time.sleep(0.2)

    detail = f"{type(last_error).__name__}: {last_error}" if last_error else "unknown"
    raise ScopeError(f"Failed to fetch datasheet url: {cleaned} ({detail})")


def _read_stream_with_limit(stream: io.BufferedIOBase, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = stream.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ScopeError(f"Datasheet exceeds max size limit ({max_bytes} bytes)")
        chunks.append(chunk)
    return b"".join(chunks)


def _lcsc_wmsc_fallback_url(url: str) -> str | None:
    lowered = url.lower()
    if "lcsc.com" not in lowered or "wmsc.lcsc.com" in lowered:
        return None
    match = _LCSC_ID_RE.search(url)
    if not match:
        return None
    lcsc_id = match.group(1).upper()
    return f"https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/{lcsc_id}.pdf"


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

    # Do not trust source suffix/content-type alone as many datasheet hosts
    # return HTML landing pages while keeping ".pdf" URLs.
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
) -> dict[str, object]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ScopeError(
            "PDF extraction requires pypdf. Install dependency and retry."
        ) from exc

    try:
        reader = PdfReader(io.BytesIO(raw_bytes))
    except Exception as exc:
        raise ScopeError(f"Failed to parse PDF datasheet: {exc}") from exc

    total_pages = len(reader.pages)
    if total_pages == 0:
        raise ScopeError("PDF datasheet has no pages")
    if start_page > total_pages:
        raise ScopeError(
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


def _decode_datasheet_bytes(raw_bytes: bytes) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ScopeError("Datasheet content could not be decoded as text")


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


def rename_path(
    project_root: Path,
    old_path: str,
    new_path: str,
    *,
    overwrite: bool = False,
) -> dict:
    source_path = resolve_scoped_path(project_root, old_path)
    destination_path = resolve_scoped_path(project_root, new_path)

    if source_path == project_root:
        raise ScopeError("Refusing to rename project root")
    if destination_path == project_root:
        raise ScopeError("Refusing to rename to project root")
    if source_path == destination_path:
        raise ScopeError("old_path and new_path must be different")
    if not source_path.exists():
        raise ScopeError(f"Path does not exist: {old_path}")

    source_kind = (
        "symlink"
        if source_path.is_symlink()
        else "directory"
        if source_path.is_dir()
        else "file"
    )

    destination_exists = destination_path.exists()
    if destination_exists:
        if not overwrite:
            raise ScopeError(f"Destination already exists: {new_path}")
        destination_kind = (
            "symlink"
            if destination_path.is_symlink()
            else "directory"
            if destination_path.is_dir()
            else "file"
        )
        if source_kind != destination_kind:
            raise ScopeError(
                "Cannot overwrite different path kind "
                f"({source_kind} -> {destination_kind})"
            )
        if destination_kind == "directory":
            shutil.rmtree(destination_path)
        else:
            destination_path.unlink()

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.rename(destination_path)

    return {
        "old_path": str(source_path.relative_to(project_root)),
        "new_path": str(destination_path.relative_to(project_root)),
        "kind": source_kind,
        "overwrote": bool(destination_exists),
    }


def delete_path(
    project_root: Path,
    path: str,
    *,
    recursive: bool = True,
) -> dict:
    target_path = resolve_scoped_path(project_root, path)

    if target_path == project_root:
        raise ScopeError("Refusing to delete project root")
    if not target_path.exists():
        raise ScopeError(f"Path does not exist: {path}")

    if target_path.is_symlink():
        kind = "symlink"
        target_path.unlink()
    elif target_path.is_dir():
        kind = "directory"
        if recursive:
            shutil.rmtree(target_path)
        else:
            try:
                target_path.rmdir()
            except OSError as exc:
                raise ScopeError(
                    "Directory is not empty; set recursive=true to delete"
                ) from exc
    else:
        kind = "file"
        target_path.unlink()

    return {
        "path": str(target_path.relative_to(project_root)),
        "kind": kind,
        "deleted": True,
    }


def apply_text_replace(
    project_root: Path,
    path: str,
    find_text: str,
    replace_with: str,
    *,
    max_replacements: int = 1,
) -> dict:
    if not find_text:
        raise ScopeError("find_text must not be empty")
    if max_replacements < 1:
        raise ScopeError("max_replacements must be >= 1")

    file_path = resolve_scoped_path(project_root, path)
    if not file_path.exists() or not file_path.is_file():
        raise ScopeError(f"File does not exist: {path}")

    text = file_path.read_text(encoding="utf-8")
    count = text.count(find_text)
    if count == 0:
        raise ScopeError("find_text was not found in file")

    replaced = text.replace(find_text, replace_with, max_replacements)
    file_path.write_text(replaced, encoding="utf-8")

    return {
        "path": str(file_path.relative_to(project_root)),
        "matches": count,
        "replacements": min(count, max_replacements),
    }


def apply_hashline_edits(project_root: Path, path: str, edits: list[dict]) -> dict:
    """Apply a batch of hash-anchored edits atomically to a project file."""
    file_path = resolve_scoped_path(project_root, path)
    if not file_path.exists() or not file_path.is_file():
        raise ScopeError(f"File does not exist: {path}")

    raw_content = file_path.read_text(encoding="utf-8")
    line_ending = _detect_line_ending(raw_content)
    had_trailing_newline = _has_trailing_newline(raw_content)

    normalized_content = _normalize_newlines(raw_content)
    original_lines = normalized_content.splitlines()

    operations = _parse_hashline_operations(edits)
    _validate_non_overlapping_operations(operations)

    mismatches = _collect_hash_mismatches(operations, original_lines)
    if mismatches:
        raise HashlineMismatchError(mismatches, original_lines)

    updated_lines = list(original_lines)
    first_changed_line: int | None = None
    operations_applied = 0
    noop_details: list[str] = []

    for operation in sorted(operations, key=_operation_sort_key, reverse=True):
        if isinstance(operation, SetLineOperation):
            start_idx = operation.anchor.line - 1
            old_lines = updated_lines[start_idx : start_idx + 1]
            new_lines = _split_replacement_lines(operation.new_text)
            if old_lines == new_lines:
                noop_details.append(
                    "edits[{}] set_line at {}:{}".format(
                        operation.index,
                        operation.anchor.line,
                        operation.anchor.hash,
                    )
                )
                continue

            updated_lines[start_idx : start_idx + 1] = new_lines
            operations_applied += 1
            first_changed_line = _min_changed_line(
                first_changed_line, operation.anchor.line
            )
            continue

        if isinstance(operation, ReplaceLinesOperation):
            start_idx = operation.start_anchor.line - 1
            end_idx = operation.end_anchor.line
            old_lines = updated_lines[start_idx:end_idx]
            new_lines = _split_replacement_lines(operation.new_text)
            if old_lines == new_lines:
                noop_details.append(
                    "edits[{}] replace_lines {}:{} -> {}:{}".format(
                        operation.index,
                        operation.start_anchor.line,
                        operation.start_anchor.hash,
                        operation.end_anchor.line,
                        operation.end_anchor.hash,
                    )
                )
                continue

            updated_lines[start_idx:end_idx] = new_lines
            operations_applied += 1
            first_changed_line = _min_changed_line(
                first_changed_line, operation.start_anchor.line
            )
            continue

        insert_lines = _split_insert_lines(operation.text)
        insert_idx = operation.anchor.line
        updated_lines[insert_idx:insert_idx] = insert_lines
        operations_applied += 1
        first_changed_line = _min_changed_line(
            first_changed_line, operation.anchor.line + 1
        )

    if operations_applied == 0:
        message = "No changes made. All edit operations were no-ops."
        if noop_details:
            details = "\n".join(f"- {detail}" for detail in noop_details)
            message = f"{message}\n{details}"
        raise ScopeError(message)

    if updated_lines == original_lines:
        raise ScopeError(
            "No changes made. Edit operations cancelled out to identical content."
        )

    normalized_output = "\n".join(updated_lines)
    output = _restore_line_endings(normalized_output, line_ending)
    output = _restore_trailing_newline(
        output,
        line_ending=line_ending,
        had_trailing_newline=had_trailing_newline,
    )

    output_bytes = len(output.encode("utf-8"))
    if output_bytes > _MAX_WRITE_FILE_BYTES:
        raise ScopeError("Refusing to write very large file content")

    relative_path = str(file_path.relative_to(project_root))
    diff_summary = _build_diff_summary(
        relative_path=relative_path,
        before_lines=original_lines,
        after_lines=updated_lines,
    )
    ui_payload = _build_ui_diff_payload(
        relative_path=relative_path,
        before_text=raw_content,
        after_text=output,
    )

    file_path.write_text(output, encoding="utf-8")

    response: dict[str, object] = {
        "path": relative_path,
        "operations_requested": len(operations),
        "operations_applied": operations_applied,
        "first_changed_line": first_changed_line,
        "total_lines": len(updated_lines),
        "bytes": output_bytes,
        "diff": diff_summary,
    }
    if ui_payload is not None:
        response["_ui"] = {"edit_diff": ui_payload}
    return response


def search_in_files(
    project_root: Path,
    query: str,
    *,
    limit: int = 50,
) -> list[MatchLine]:
    needle = query.strip().lower()
    if not needle:
        return []

    matches: list[MatchLine] = []
    for path in project_root.rglob("*"):
        if len(matches) >= limit:
            break
        if not is_context_file(path, project_root):
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for idx, line in enumerate(text.splitlines(), start=1):
            if needle not in line.lower():
                continue
            matches.append(
                MatchLine(
                    path=str(path.relative_to(project_root)),
                    line=idx,
                    text=line.strip()[:260],
                )
            )
            if len(matches) >= limit:
                break

    return matches


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _detect_line_ending(text: str) -> Literal["\n", "\r\n", "\r"]:
    if "\r\n" in text:
        return "\r\n"
    if "\r" in text:
        return "\r"
    return "\n"


def _has_trailing_newline(text: str) -> bool:
    return text.endswith("\n") or text.endswith("\r")


def _restore_line_endings(text: str, line_ending: Literal["\n", "\r\n", "\r"]) -> str:
    if line_ending == "\n":
        return text
    return text.replace("\n", line_ending)


def _restore_trailing_newline(
    text: str,
    *,
    line_ending: Literal["\n", "\r\n", "\r"],
    had_trailing_newline: bool,
) -> str:
    if had_trailing_newline:
        if text:
            if not text.endswith(line_ending):
                return text + line_ending
            return text
        return line_ending

    while text.endswith(line_ending):
        text = text[: -len(line_ending)]
    return text


def _split_replacement_lines(text: str) -> list[str]:
    normalized = _normalize_newlines(text)
    if normalized == "":
        return []
    return normalized.split("\n")


def _split_insert_lines(text: str) -> list[str]:
    normalized = _normalize_newlines(text)
    if normalized == "":
        raise ScopeError("insert_after.text must be non-empty")
    return normalized.split("\n")


def _parse_hashline_operations(edits: list[dict]) -> list[EditOperation]:
    if not isinstance(edits, list):
        raise ScopeError("edits must be an array")
    if not edits:
        raise ScopeError("edits must not be empty")

    operations: list[EditOperation] = []
    for idx, raw_edit in enumerate(edits):
        if not isinstance(raw_edit, dict):
            raise ScopeError(f"edits[{idx}] must be an object")
        if len(raw_edit) != 1:
            raise ScopeError(
                "edits[{}] must contain exactly one key: set_line, "
                "replace_lines, or insert_after".format(idx)
            )

        if "set_line" in raw_edit:
            payload = _validate_edit_payload(
                raw_edit["set_line"],
                ["anchor", "new_text"],
                idx,
                "set_line",
            )
            operations.append(
                SetLineOperation(
                    index=idx,
                    anchor=parse_line_anchor(payload["anchor"]),
                    new_text=payload["new_text"],
                )
            )
            continue

        if "replace_lines" in raw_edit:
            payload = _validate_edit_payload(
                raw_edit["replace_lines"],
                ["start_anchor", "end_anchor", "new_text"],
                idx,
                "replace_lines",
            )
            start_anchor = parse_line_anchor(payload["start_anchor"])
            end_anchor = parse_line_anchor(payload["end_anchor"])
            if start_anchor.line > end_anchor.line:
                raise ScopeError(
                    f"edits[{idx}] replace_lines.start_anchor must be <= end_anchor"
                )
            operations.append(
                ReplaceLinesOperation(
                    index=idx,
                    start_anchor=start_anchor,
                    end_anchor=end_anchor,
                    new_text=payload["new_text"],
                )
            )
            continue

        if "insert_after" in raw_edit:
            payload = _validate_edit_payload(
                raw_edit["insert_after"],
                ["anchor", "text"],
                idx,
                "insert_after",
            )
            operations.append(
                InsertAfterOperation(
                    index=idx,
                    anchor=parse_line_anchor(payload["anchor"]),
                    text=payload["text"],
                )
            )
            continue

        raise ScopeError(
            f"edits[{idx}] must contain one of set_line, replace_lines, or insert_after"
        )

    return operations


def _validate_edit_payload(
    payload: object,
    required_keys: list[str],
    edit_index: int,
    variant: str,
) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise ScopeError(f"edits[{edit_index}].{variant} must be an object")

    unknown_keys = [key for key in payload if key not in required_keys]
    missing_keys = [key for key in required_keys if key not in payload]
    if unknown_keys or missing_keys:
        raise ScopeError(
            f"edits[{edit_index}].{variant} must contain only keys {required_keys}"
        )

    validated: dict[str, str] = {}
    for key in required_keys:
        value = payload[key]
        if not isinstance(value, str):
            raise ScopeError(f"edits[{edit_index}].{variant}.{key} must be a string")
        validated[key] = value

    if variant == "insert_after" and validated["text"] == "":
        raise ScopeError(f"edits[{edit_index}].insert_after.text must be non-empty")

    return validated


def _collect_hash_mismatches(
    operations: list[EditOperation],
    file_lines: list[str],
) -> list[HashlineMismatch]:
    mismatches: dict[tuple[int, str, str], HashlineMismatch] = {}

    for operation in operations:
        for anchor in _anchors_for_operation(operation):
            if anchor.line < 1 or anchor.line > len(file_lines):
                raise ScopeError(
                    "Anchor line {} is out of range (file has {} lines)".format(
                        anchor.line,
                        len(file_lines),
                    )
                )

            actual_hash = compute_line_hash(anchor.line, file_lines[anchor.line - 1])
            if actual_hash == anchor.hash:
                continue

            key = (anchor.line, anchor.hash, actual_hash)
            mismatches[key] = HashlineMismatch(
                line=anchor.line,
                expected=anchor.hash,
                actual=actual_hash,
            )

    return sorted(
        mismatches.values(),
        key=lambda mismatch: (mismatch.line, mismatch.expected),
    )


def _anchors_for_operation(operation: EditOperation) -> list[LineAnchor]:
    if isinstance(operation, SetLineOperation):
        return [operation.anchor]
    if isinstance(operation, ReplaceLinesOperation):
        return [operation.start_anchor, operation.end_anchor]
    return [operation.anchor]


def _operation_sort_key(operation: EditOperation) -> tuple[int, int]:
    if isinstance(operation, ReplaceLinesOperation):
        return (operation.end_anchor.line, operation.index)
    if isinstance(operation, SetLineOperation):
        return (operation.anchor.line, operation.index)
    return (operation.anchor.line, operation.index)


def _validate_non_overlapping_operations(operations: list[EditOperation]) -> None:
    spans = [_operation_span(operation) for operation in operations]

    for index, first in enumerate(spans):
        for second in spans[index + 1 :]:
            if not _spans_overlap(first, second):
                continue
            raise ScopeError(
                "Overlapping edit spans between edits[{}] ({}) and edits[{}] ({})"
                .format(first[2], first[3], second[2], second[3])
            )


def _operation_span(operation: EditOperation) -> tuple[int, int, int, str, bool]:
    if isinstance(operation, SetLineOperation):
        line = operation.anchor.line
        return (line, line, operation.index, "set_line", False)
    if isinstance(operation, ReplaceLinesOperation):
        return (
            operation.start_anchor.line,
            operation.end_anchor.line,
            operation.index,
            "replace_lines",
            False,
        )

    line = operation.anchor.line
    return (line, line, operation.index, "insert_after", True)


def _spans_overlap(
    first: tuple[int, int, int, str, bool],
    second: tuple[int, int, int, str, bool],
) -> bool:
    first_start, first_end, _, _, first_insert = first
    second_start, second_end, _, _, second_insert = second

    if first_insert and second_insert:
        return first_start == second_start

    if first_insert:
        return second_start <= first_start <= second_end

    if second_insert:
        return first_start <= second_start <= first_end

    return not (first_end < second_start or second_end < first_start)


def _min_changed_line(current: int | None, candidate: int) -> int:
    if current is None:
        return candidate
    return min(current, candidate)


def _format_mismatch_error(
    mismatches: list[HashlineMismatch],
    file_lines: list[str],
) -> str:
    mismatch_lines = {mismatch.line for mismatch in mismatches}
    display_lines: set[int] = set()

    for mismatch in mismatches:
        start = max(1, mismatch.line - _HASHLINE_CONTEXT_LINES)
        end = min(len(file_lines), mismatch.line + _HASHLINE_CONTEXT_LINES)
        display_lines.update(range(start, end + 1))

    heading = (
        "{} line{} changed since last read. Use updated LINE:HASH refs shown "
        "below (>>> marks changed lines)."
    )
    output = [
        heading.format(
            len(mismatches),
            "s" if len(mismatches) != 1 else "",
        ),
        "",
    ]

    ordered_lines = sorted(display_lines)
    previous_line = -1
    for line_number in ordered_lines:
        if previous_line != -1 and line_number > previous_line + 1:
            output.append("    ...")
        previous_line = line_number

        content = file_lines[line_number - 1]
        actual_hash = compute_line_hash(line_number, content)
        prefix = f"{line_number}:{actual_hash}|{content}"
        if line_number in mismatch_lines:
            output.append(f">>> {prefix}")
        else:
            output.append(f"    {prefix}")

    output.append("")
    output.append("Quick fix - replace stale refs:")
    for mismatch in mismatches:
        old_ref = f"{mismatch.line}:{mismatch.expected}"
        new_ref = f"{mismatch.line}:{mismatch.actual}"
        output.append(
            f"  {old_ref} -> {new_ref}"
        )

    return "\n".join(output)


def _build_diff_summary(
    *,
    relative_path: str,
    before_lines: list[str],
    after_lines: list[str],
) -> dict[str, object]:
    diff_lines = list(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
            lineterm="",
        )
    )
    added_lines = 0
    removed_lines = 0
    hunks = 0
    for line in diff_lines:
        if line.startswith("@@"):
            hunks += 1
        elif line.startswith("+") and not line.startswith("+++"):
            added_lines += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed_lines += 1

    preview_limit = 140
    preview_lines = diff_lines[:preview_limit]
    return {
        "added_lines": added_lines,
        "removed_lines": removed_lines,
        "hunks": hunks,
        "preview": "\n".join(preview_lines),
        "truncated": len(diff_lines) > preview_limit,
    }


def _build_ui_diff_payload(
    *,
    relative_path: str,
    before_text: str,
    after_text: str,
) -> dict[str, object] | None:
    before_size = len(before_text.encode("utf-8"))
    after_size = len(after_text.encode("utf-8"))
    if before_size > _MAX_UI_DIFF_BYTES or after_size > _MAX_UI_DIFF_BYTES:
        return None

    return {
        "path": relative_path,
        "before_content": before_text,
        "after_content": after_text,
    }
