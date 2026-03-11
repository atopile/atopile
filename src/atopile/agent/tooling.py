"""Tool directory and suggestion helpers for the rewrite-native agent service."""

from __future__ import annotations

from typing import Any

from atopile.agent import mediator

from .api_models import (
    DETAIL_PROJECT_ROOT_MISMATCH,
    OTHER_CATEGORY,
    AgentServiceError,
    ToolDirectoryResponse,
    ToolSuggestionsRequest,
    ToolSuggestionsResponse,
    session_not_found_detail,
)
from .session_store import sessions_by_id, sessions_lock


async def get_tool_directory(session_id: str | None = None) -> ToolDirectoryResponse:
    """Return available tools plus context-aware suggestions."""
    tool_memory: dict[str, dict[str, Any]] = {}
    history: list[dict[str, str]] = []
    selected_targets: list[str] = []

    if session_id:
        with sessions_lock:
            session = sessions_by_id.get(session_id)
        if not session:
            raise AgentServiceError(
                404,
                session_not_found_detail(session_id),
            )
        tool_memory = dict(session.tool_memory)
        history = list(session.history)
        selected_targets = list(session.recent_selected_targets)

    directory = mediator.get_tool_directory()
    categories = sorted(
        {str(item.get("category", OTHER_CATEGORY)) for item in directory}
    )
    suggestions = mediator.suggest_tools(
        message="",
        history=history,
        selected_targets=selected_targets,
        tool_memory=tool_memory,
        limit=3,
    )
    memory_view = mediator.get_tool_memory_view(tool_memory)

    return ToolDirectoryResponse(
        tools=directory,
        categories=categories,
        suggestions=suggestions,
        toolMemory=memory_view,
    )


async def get_tool_suggestions(
    session_id: str,
    request: ToolSuggestionsRequest,
) -> ToolSuggestionsResponse:
    """Return tool suggestions for the current prompt and session context."""
    with sessions_lock:
        session = sessions_by_id.get(session_id)
    if not session:
        raise AgentServiceError(
            404,
            session_not_found_detail(session_id),
        )

    if request.project_root and request.project_root != session.project_root:
        raise AgentServiceError(400, DETAIL_PROJECT_ROOT_MISMATCH)

    selected_targets = (
        list(request.selected_targets)
        if request.selected_targets
        else list(session.recent_selected_targets)
    )
    suggestions = mediator.suggest_tools(
        message=request.message,
        history=list(session.history),
        selected_targets=selected_targets,
        tool_memory=session.tool_memory,
        limit=3,
    )
    memory_view = mediator.get_tool_memory_view(session.tool_memory)

    return ToolSuggestionsResponse(
        suggestions=suggestions,
        toolMemory=memory_view,
    )
