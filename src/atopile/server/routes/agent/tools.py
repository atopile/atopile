"""Tool-directory and suggestion routes for the agent API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from atopile.server.agent import mediator

from .models import (
    DETAIL_PROJECT_ROOT_MISMATCH,
    OTHER_CATEGORY,
    ToolDirectoryResponse,
    ToolSuggestionsRequest,
    ToolSuggestionsResponse,
    session_not_found_detail,
)
from .utils import sessions_by_id, sessions_lock

router = APIRouter()


@router.get("/tools", response_model=ToolDirectoryResponse)
async def get_tool_directory(
    session_id: str | None = Query(default=None, alias="sessionId"),
):
    """Return available tools plus context-aware suggestions."""
    tool_memory: dict[str, dict[str, Any]] = {}
    history: list[dict[str, str]] = []
    selected_targets: list[str] = []

    if session_id:
        with sessions_lock:
            session = sessions_by_id.get(session_id)
        if not session:
            raise HTTPException(
                status_code=404, detail=session_not_found_detail(session_id)
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


@router.post(
    "/sessions/{session_id}/tool-suggestions",
    response_model=ToolSuggestionsResponse,
)
async def get_tool_suggestions(
    session_id: str,
    request: ToolSuggestionsRequest,
):
    """Return tool suggestions for the current prompt and session context."""
    with sessions_lock:
        session = sessions_by_id.get(session_id)
    if not session:
        raise HTTPException(
            status_code=404, detail=session_not_found_detail(session_id)
        )

    if request.project_root and request.project_root != session.project_root:
        raise HTTPException(status_code=400, detail=DETAIL_PROJECT_ROOT_MISMATCH)

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
