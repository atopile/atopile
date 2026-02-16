"""Agent scope and file-access policy helpers."""

from __future__ import annotations

import difflib
import hashlib
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from atopile.dataclasses import AppContext
from atopile.server.agent import policy_datasheet
from atopile.server.agent import policy_scope

_MAX_WRITE_FILE_BYTES = 600_000
_MAX_UI_DIFF_BYTES = 220_000
_HASH_HEX_CHARS = 4
_HASHLINE_CONTEXT_LINES = 2
_ALLOWED_CREATE_FILE_EXTENSIONS: tuple[str, ...] = (".ato", ".md", ".py")
_FABLL_PY_CREATE_ROOTS: tuple[Path, ...] = (Path("src/faebryk/library"),)

_ANCHOR_RE = re.compile(r"^(\d+)\s*:\s*([0-9A-Za-z]{1,16})$")
_ANCHOR_PREFIX_RE = re.compile(r"^(\d+)\s*:\s*([0-9A-Za-z]{1,16})")


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
    return policy_scope.resolve_project_root(
        project_root, ctx, scope_error_cls=ScopeError
    )


def resolve_scoped_path(project_root: Path, path: str) -> Path:
    return policy_scope.resolve_scoped_path(
        project_root, path, scope_error_cls=ScopeError
    )


def _resolve_readable_file_path(
    project_root: Path,
    path: str,
) -> tuple[Path, str]:
    return policy_scope.resolve_readable_file_path(
        project_root,
        path,
        resolve_scoped_path_fn=resolve_scoped_path,
        scope_error_cls=ScopeError,
    )


def is_context_file(path: Path, project_root: Path) -> bool:
    return policy_scope.is_context_file(path, project_root)


def list_context_files(project_root: Path, limit: int = 300) -> list[str]:
    return policy_scope.list_context_files(project_root, limit=limit)


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
        raise ScopeError(f"Invalid anchor '{raw_anchor}'. {expected}")

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
    return policy_datasheet.read_datasheet_file(
        project_root,
        path=path,
        url=url,
        resolve_scoped_path=resolve_scoped_path,
        scope_error_cls=ScopeError,
    )


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
    return policy_datasheet.read_datasheet_content(
        project_root,
        path=path,
        url=url,
        start_page=start_page,
        max_pages=max_pages,
        query=query,
        max_chars=max_chars,
        resolve_scoped_path=resolve_scoped_path,
        scope_error_cls=ScopeError,
    )


def create_path(
    project_root: Path,
    path: str,
    *,
    kind: Literal["file", "directory"] = "file",
    content: str = "",
    overwrite: bool = False,
    parents: bool = True,
) -> dict:
    raw_path = path.strip()
    if not raw_path:
        raise ScopeError("path must not be empty")

    target_path = resolve_scoped_path(project_root, raw_path)
    if target_path == project_root:
        raise ScopeError("Refusing to create project root path")

    if kind not in {"file", "directory"}:
        raise ScopeError("kind must be 'file' or 'directory'")

    if kind == "directory":
        if content:
            raise ScopeError("content is only supported when kind='file'")
        if target_path.exists() and not target_path.is_dir():
            raise ScopeError(f"Path already exists and is not a directory: {path}")
        if not parents and not target_path.parent.exists():
            raise ScopeError("Parent directory does not exist; set parents=true")

        existed = target_path.exists()
        target_path.mkdir(parents=parents, exist_ok=True)
        return {
            "path": str(target_path.relative_to(project_root)),
            "kind": "directory",
            "created": not existed,
        }

    extension = target_path.suffix.lower()
    if extension not in _ALLOWED_CREATE_FILE_EXTENSIONS:
        allowed = ", ".join(_ALLOWED_CREATE_FILE_EXTENSIONS)
        raise ScopeError(f"Only {allowed} files can be created with this tool.")

    relative_target = target_path.relative_to(project_root)
    if extension == ".py" and not any(
        relative_target == allowed_root or relative_target.is_relative_to(allowed_root)
        for allowed_root in _FABLL_PY_CREATE_ROOTS
    ):
        allowed_roots = ", ".join(str(root) for root in _FABLL_PY_CREATE_ROOTS)
        raise ScopeError(
            f"Python files may only be created for fabll modules under: {allowed_roots}"
        )

    if target_path.exists():
        if target_path.is_dir():
            raise ScopeError(f"Path already exists and is a directory: {path}")
        if not overwrite:
            raise ScopeError(f"File already exists: {path}")
        overwrote = True
    else:
        overwrote = False

    if not parents and not target_path.parent.exists():
        raise ScopeError("Parent directory does not exist; set parents=true")

    content_bytes = len(content.encode("utf-8"))
    if content_bytes > _MAX_WRITE_FILE_BYTES:
        raise ScopeError("Refusing to write very large file content")

    target_path.parent.mkdir(parents=parents, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")

    return {
        "path": str(relative_target),
        "kind": "file",
        "extension": extension,
        "bytes": content_bytes,
        "created": not overwrote,
        "overwrote": overwrote,
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
                "Overlapping edit spans between "
                f"edits[{first[2]}] ({first[3]}) and "
                f"edits[{second[2]}] ({second[3]})"
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
        output.append(f"  {old_ref} -> {new_ref}")

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
