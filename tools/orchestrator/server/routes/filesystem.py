"""API routes for filesystem operations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/filesystem", tags=["filesystem"])


class PathSuggestion(BaseModel):
    """A single path suggestion."""

    path: str
    name: str
    is_directory: bool


class PathCompletionResponse(BaseModel):
    """Response for path completion requests."""

    suggestions: list[PathSuggestion]
    base_path: str
    query: str


@router.get("/complete", response_model=PathCompletionResponse)
async def complete_path(
    query: str = Query(default="", description="The path prefix to complete"),
    base_path: Optional[str] = Query(default=None, description="Base path to resolve relative paths"),
    directories_only: bool = Query(default=False, description="Only return directories"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of suggestions"),
) -> PathCompletionResponse:
    """Complete a filesystem path.

    This endpoint provides path completion suggestions similar to shell tab completion.
    It handles:
    - Absolute paths (starting with /)
    - Relative paths (resolved against base_path or cwd)
    - Home directory expansion (~)
    - Partial path completion
    - Fuzzy recursive search when query doesn't contain /
    """
    suggestions: list[PathSuggestion] = []

    # Determine the effective base path
    if base_path:
        effective_base = Path(base_path).expanduser().resolve()
    else:
        effective_base = Path.cwd()

    # Handle empty query - show contents of base path
    if not query:
        try:
            for entry in sorted(effective_base.iterdir()):
                if directories_only and not entry.is_dir():
                    continue
                suggestions.append(
                    PathSuggestion(
                        path=str(entry),
                        name=entry.name,
                        is_directory=entry.is_dir(),
                    )
                )
                if len(suggestions) >= limit:
                    break
        except PermissionError:
            pass
        return PathCompletionResponse(
            suggestions=suggestions,
            base_path=str(effective_base),
            query=query,
        )

    # Expand ~ to home directory
    expanded_query = os.path.expanduser(query)

    # Determine if this is an absolute or relative path
    if os.path.isabs(expanded_query):
        search_path = Path(expanded_query)
    else:
        search_path = effective_base / expanded_query

    # If the query ends with a separator, list the directory contents
    if query.endswith(os.sep) or query.endswith("/"):
        try:
            if search_path.is_dir():
                for entry in sorted(search_path.iterdir()):
                    if directories_only and not entry.is_dir():
                        continue
                    # Return the full path that includes the query prefix
                    if os.path.isabs(expanded_query):
                        result_path = str(entry)
                    else:
                        result_path = query + entry.name
                    suggestions.append(
                        PathSuggestion(
                            path=result_path,
                            name=entry.name,
                            is_directory=entry.is_dir(),
                        )
                    )
                    if len(suggestions) >= limit:
                        break
        except PermissionError:
            pass
    elif "/" not in query and not os.path.isabs(expanded_query):
        # No slash in query - do recursive fuzzy search
        # This allows typing "quickstart" to find "examples/quickstart/quickstart.ato"
        partial_name = query.lower()

        # Skip common directories that are large/not useful
        skip_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build', '.tox', '.pytest_cache', '.mypy_cache'}

        def search_recursive(directory: Path, depth: int = 0, max_depth: int = 5):
            """Recursively search for matching files/directories."""
            if depth > max_depth:
                return
            try:
                for entry in sorted(directory.iterdir()):
                    if entry.name in skip_dirs:
                        continue
                    if entry.name.startswith('.') and not partial_name.startswith('.'):
                        # Skip hidden files unless searching for hidden files
                        continue

                    if entry.name.lower().startswith(partial_name):
                        if directories_only and not entry.is_dir():
                            continue
                        # Return path relative to effective_base
                        try:
                            rel_path = entry.relative_to(effective_base)
                            suggestions.append(
                                PathSuggestion(
                                    path=str(rel_path),
                                    name=entry.name,
                                    is_directory=entry.is_dir(),
                                )
                            )
                        except ValueError:
                            pass
                        if len(suggestions) >= limit:
                            return

                    # Recurse into directories
                    if entry.is_dir() and len(suggestions) < limit:
                        search_recursive(entry, depth + 1, max_depth)
                        if len(suggestions) >= limit:
                            return
            except PermissionError:
                pass

        search_recursive(effective_base)

        # Sort by path length (prefer shorter/closer matches)
        suggestions.sort(key=lambda s: (len(s.path), s.path))
        suggestions = suggestions[:limit]
    else:
        # Complete the partial path (contains /)
        parent = search_path.parent
        partial_name = search_path.name.lower()

        try:
            if parent.is_dir():
                for entry in sorted(parent.iterdir()):
                    if directories_only and not entry.is_dir():
                        continue
                    if entry.name.lower().startswith(partial_name):
                        # Construct the result path preserving the original query style
                        if os.path.isabs(expanded_query):
                            result_path = str(entry)
                        else:
                            # Preserve the relative path style
                            relative_parent = query.rsplit("/", 1)[0] if "/" in query else ""
                            if relative_parent:
                                result_path = relative_parent + "/" + entry.name
                            else:
                                result_path = entry.name
                        suggestions.append(
                            PathSuggestion(
                                path=result_path,
                                name=entry.name,
                                is_directory=entry.is_dir(),
                            )
                        )
                        if len(suggestions) >= limit:
                            break
        except PermissionError:
            pass

    return PathCompletionResponse(
        suggestions=suggestions,
        base_path=str(effective_base),
        query=query,
    )
