"""Resolve domain logic - business logic for address resolution."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from atopile.dataclasses import AppContext


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

    if not source_file and ctx.workspace_path:
        ws_path = ctx.workspace_path
        candidate = ws_path / file_part
        if candidate.exists():
            source_file = candidate
        else:
            for ato_file in ws_path.rglob(file_part):
                source_file = ato_file
                break

    if not source_file or not source_file.exists():
        raise FileNotFoundError(f"Source file not found: {file_part}")

    path_segments = []
    current = ""
    for char in path_part:
        if char == ".":
            if current:
                path_segments.append(current)
            current = ""
        elif char == "[":
            if current:
                path_segments.append(current)
            current = "["
        elif char == "]":
            current += char
            path_segments.append(current)
            current = ""
        else:
            current += char
    if current:
        path_segments.append(current)

    content = source_file.read_text()
    line_number = 1
    found = False

    if path_segments:
        first_segment = path_segments[0]
        block_pattern = re.compile(
            rf"^\s*(module|interface|component)\s+{re.escape(first_segment)}\s*[:(]",
            re.MULTILINE,
        )
        match = block_pattern.search(content)
        if match:
            line_number = content[: match.start()].count("\n") + 1
            found = True

            if len(path_segments) > 1:
                last_field = path_segments[-1]
                field_name = re.sub(r"\[\d+\]$", "", last_field)

                block_content = content[match.start() :]
                field_patterns = [
                    rf"^\s*{re.escape(field_name)}\s*=",
                    rf"^\s*{re.escape(field_name)}\s*:",
                    rf"^\s*{re.escape(field_name)}\s*=\s*new\s+",
                ]

                for pattern in field_patterns:
                    field_match = re.search(pattern, block_content, re.MULTILINE)
                    if field_match:
                        line_number = (
                            content[: match.start()].count("\n")
                            + block_content[: field_match.start()].count("\n")
                            + 1
                        )
                        found = True
                        break

    if not found:
        line_number = 1

    return {
        "file": str(source_file.absolute()),
        "line": line_number,
        "column": 1,
        "address": address,
        "resolved": found,
    }


__all__ = [
    "handle_resolve_location",
]
