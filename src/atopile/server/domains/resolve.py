"""Resolve domain logic - business logic for address resolution."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from atopile.dataclasses import AppContext

_TOP_LEVEL_BLOCK_PATTERN = re.compile(
    r"^(module|interface|component)\s+[A-Za-z_][A-Za-z0-9_]*\s*[:(]",
    re.MULTILINE,
)


def _split_path_segments(path_part: str) -> list[str]:
    """
    Split an address path into segments while keeping index suffixes attached.

    Examples:
    - "FakeProcessor.core_caps[1]" -> ["FakeProcessor", "core_caps[1]"]
    - "Foo.bar[0].baz" -> ["Foo", "bar[0]", "baz"]
    """
    segments: list[str] = []
    current: list[str] = []
    bracket_depth = 0

    for char in path_part:
        if char == "." and bracket_depth == 0:
            if current:
                segments.append("".join(current))
                current = []
            continue

        current.append(char)
        if char == "[":
            bracket_depth += 1
        elif char == "]" and bracket_depth > 0:
            bracket_depth -= 1

    if current:
        segments.append("".join(current))

    return [segment for segment in segments if segment]


def _line_number_from_index(content: str, index: int) -> int:
    return content.count("\n", 0, index) + 1


def _column_number_from_index(content: str, index: int) -> int:
    last_newline = content.rfind("\n", 0, index)
    return index + 1 if last_newline < 0 else index - last_newline


def handle_resolve_location(
    address: str,
    project_root: Optional[str],
    ctx: AppContext,
) -> dict:
    """
    Resolve an atopile address to a source file location.

    Args:
        address: Atopile address (e.g., 'file.ato::Module.field')
        project_root: Optional project root path
        ctx: Application context with workspace paths

    Returns:
        Dict with file, line, column, address, and resolved status

    Raises:
        ValueError: If address format is invalid
        FileNotFoundError: If source file cannot be found
    """
    if not address:
        raise ValueError("Missing address")

    address = address.strip()
    if "|" in address:
        address = address.split("|")[0]

    if "::" not in address:
        raise ValueError(
            f"Invalid address format: {address}. Expected 'file.ato::path'"
        )

    file_part, path_part = address.split("::", 1)

    source_file = None

    if project_root:
        project_path = Path(project_root)
        candidate = project_path / file_part
        if candidate.exists():
            source_file = candidate

        if not source_file:
            modules_dir = project_path / ".ato" / "modules"
            if modules_dir.exists():
                for ato_file in modules_dir.rglob(file_part):
                    source_file = ato_file
                    break

    if not source_file:
        candidate = Path(file_part)
        if candidate.exists():
            source_file = candidate

    if not source_file and ctx.workspace_paths:
        ws_path = ctx.workspace_paths[0]
        candidate = ws_path / file_part
        if candidate.exists():
            source_file = candidate
        else:
            for ato_file in ws_path.rglob(file_part):
                source_file = ato_file
                break

    if not source_file or not source_file.exists():
        raise FileNotFoundError(f"Source file not found: {file_part}")

    path_segments = _split_path_segments(path_part)

    content = source_file.read_text()
    line_number = 1
    column_number = 1
    found = False

    if path_segments:
        first_segment = path_segments[0]
        block_pattern = re.compile(
            rf"^[ \t]*(module|interface|component)\s+{re.escape(first_segment)}\s*[:(]",
            re.MULTILINE,
        )
        match = block_pattern.search(content)
        if match:
            block_start = match.start()
            line_number = _line_number_from_index(content, block_start)
            column_number = _column_number_from_index(content, block_start)
            found = True

            next_block = _TOP_LEVEL_BLOCK_PATTERN.search(content, match.end())
            block_end = next_block.start() if next_block else len(content)
            block_content = content[block_start:block_end]

            if len(path_segments) > 1:
                last_field = path_segments[-1]
                field_name = re.sub(r"(?:\[\d+\])+$", "", last_field)

                if field_name:
                    field_patterns = [
                        rf"^[ \t]*{re.escape(field_name)}\s*=",
                        rf"^[ \t]*{re.escape(field_name)}\s*:",
                        rf"^[ \t]*{re.escape(field_name)}\s*=\s*new\s+",
                    ]

                    for pattern in field_patterns:
                        field_match = re.search(pattern, block_content, re.MULTILINE)
                        if field_match:
                            field_start = block_start + field_match.start()
                            line_number = _line_number_from_index(content, field_start)
                            column_number = _column_number_from_index(
                                content, field_start
                            )
                            found = True
                            break

    if not found:
        line_number = 1
        column_number = 1

    abs_source = str(source_file.absolute())
    return {
        "file": abs_source,
        "file_path": abs_source,
        "line": line_number,
        "column": column_number,
        "address": address,
        "resolved": found,
    }


__all__ = [
    "handle_resolve_location",
]
