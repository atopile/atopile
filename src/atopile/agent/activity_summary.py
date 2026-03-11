"""Live activity summary generation for the agent UI."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from atopile.agent.config import AgentConfig
from atopile.agent.dataclasses import SummaryEvent, SummaryState
from atopile.agent.orchestrator_helpers import (
    _extract_text,
    _response_model_to_dict,
    trim_single_line,
)
from atopile.logging import get_logger

log = get_logger(__name__)

_TERMINAL_PHASES = {"done", "error", "stopped", "design_questions"}
_SUMMARY_PHASES = {
    "thinking",
    "tool_start",
    "tool_end",
    "compacting",
    "done",
    "error",
    "stopped",
    "design_questions",
}
_EDIT_TOOLS = {
    "project_edit_file",
    "project_create_path",
    "project_create_file",
    "project_create_folder",
    "project_move_path",
    "project_rename_path",
    "project_delete_path",
}


def _clean_text(value: Any, max_chars: int = 80) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = trim_single_line(value, max_chars)
    return trimmed or None


def _compact_path(path: str) -> str:
    normalized = path.replace("\\", "/").replace("./", "").strip("/")
    if len(normalized) <= 44:
        return normalized
    segments = [segment for segment in normalized.split("/") if segment]
    if len(segments) <= 2:
        return f"...{normalized[-41:]}"
    return f".../{'/'.join(segments[-2:])}"


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


class ActivitySummarizer:
    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self._client: AsyncOpenAI | None = None
        self._states: dict[str, SummaryState] = {}
        self._skill_text: str | None = None

    async def summarize(
        self,
        *,
        session_id: str,
        run_id: str | None,
        project_root: str,
        payload: dict[str, Any],
    ) -> str | None:
        if not self._config.activity_summary_enabled:
            return None
        phase = payload.get("phase")
        if phase not in _SUMMARY_PHASES:
            return None

        state_key = f"{session_id}:{run_id or 'sync'}"
        state = self._states.setdefault(state_key, SummaryState())
        self._record_event(state, payload)

        fallback = self._build_fallback_summary(state, payload)
        state.latest_fallback = fallback
        if not fallback:
            if phase in _TERMINAL_PHASES:
                self._states.pop(state_key, None)
            return None

        # Terminal states should be immediate and deterministic.
        if phase in _TERMINAL_PHASES:
            state.latest_summary = fallback
            self._states.pop(state_key, None)
            return fallback

        summary = fallback
        if self._should_use_model(state, fallback):
            model_summary = await self._rewrite_with_model(
                project_root=project_root,
                payload=payload,
                state=state,
                fallback=fallback,
            )
            if model_summary:
                summary = model_summary
                state.last_model_at = time.time()

        state.latest_summary = summary
        state.last_phase = phase if isinstance(phase, str) else None
        return summary

    def _record_event(self, state: SummaryState, payload: dict[str, Any]) -> None:
        phase = str(payload.get("phase") or "")
        now = time.time()
        detail = _clean_text(payload.get("detail_text"), max_chars=120)

        if phase in {"thinking", "compacting"} and detail:
            state.latest_preamble = detail

        label = phase or "activity"
        if phase == "tool_start":
            label = str(payload.get("name") or "tool")
        elif phase == "tool_end":
            trace = payload.get("trace")
            if isinstance(trace, dict):
                label = str(trace.get("name") or "tool")

        state.events.append(
            SummaryEvent(ts=now, kind=phase or "activity", label=label, detail=detail)
        )
        max_events = self._config.activity_summary_max_events
        if len(state.events) > max_events:
            state.events = state.events[-max_events:]

    def _build_fallback_summary(
        self, state: SummaryState, payload: dict[str, Any]
    ) -> str | None:
        phase = payload.get("phase")
        if phase == "thinking":
            if state.latest_preamble:
                return trim_single_line(state.latest_preamble, 72)
            return "Reviewing the current project context"
        if phase == "compacting":
            return "Compacting context to keep the run moving"
        if phase == "design_questions":
            return "Waiting on design answers before continuing"
        if phase == "error":
            error = _clean_text(payload.get("error"), max_chars=68)
            return f"Stopped on an error: {error}" if error else "Stopped on an error"
        if phase == "stopped":
            return "Run stopped"
        if phase == "done":
            return "Run complete"

        if phase == "tool_start":
            return self._summarize_tool_start(
                str(payload.get("name") or ""),
                payload.get("args") if isinstance(payload.get("args"), dict) else {},
            )
        if phase == "tool_end":
            trace = payload.get("trace")
            if isinstance(trace, dict):
                return self._summarize_tool_end(trace)
        return state.latest_summary or state.latest_fallback

    def _summarize_tool_start(self, tool_name: str, args: dict[str, Any]) -> str:
        path = _clean_text(args.get("path"), max_chars=52)
        target = _clean_text(args.get("target"), max_chars=40)
        query = _clean_text(args.get("query"), max_chars=36)
        identifier = _clean_text(
            args.get("identifier") or args.get("lcsc_id"), max_chars=28
        )
        targets = _string_list(args.get("targets"))
        if tool_name == "project_read_file":
            return (
                f"Reviewing {_compact_path(path)}"
                if path
                else "Reviewing project files"
            )
        if tool_name == "project_search":
            return (
                f'Searching the project for "{query}"'
                if query
                else "Searching the project"
            )
        if tool_name in _EDIT_TOOLS:
            return f"Editing {_compact_path(path)}" if path else "Editing project files"
        if tool_name == "build_run":
            if target:
                return f"Running a build for {target}"
            if targets:
                label = (
                    targets[0]
                    if len(targets) == 1
                    else f"{targets[0]} +{len(targets) - 1}"
                )
                return f"Running a build for {trim_single_line(label, 28)}"
            return "Running a build to validate changes"
        if tool_name == "build_logs_search":
            return "Reviewing the latest build logs"
        if tool_name in {"parts_search", "packages_search", "web_search"}:
            return (
                f'Researching "{query}"'
                if query
                else "Researching the next component choice"
            )
        if tool_name == "parts_install":
            if bool(args.get("create_package")):
                return (
                    f"Installing {identifier} and creating a local package"
                    if identifier
                    else "Installing a part and creating a local package"
                )
            return (
                f"Installing {identifier}"
                if identifier
                else "Installing the selected part"
            )
        if tool_name == "package_create_local":
            name = _clean_text(args.get("name"), max_chars=28)
            return (
                f"Creating local package {name}"
                if name
                else "Creating a local package scaffold"
            )
        if tool_name == "workspace_list_targets":
            return "Discovering package build targets"
        return "Working through the next implementation step"

    def _summarize_tool_end(self, trace: dict[str, Any]) -> str:
        tool_name = str(trace.get("name") or "")
        ok = bool(trace.get("ok"))
        args = trace.get("args") if isinstance(trace.get("args"), dict) else {}
        result = trace.get("result") if isinstance(trace.get("result"), dict) else {}
        if not ok:
            error = _clean_text(result.get("error"), max_chars=68)
            if error:
                return f"Hit an error while {tool_name.replace('_', ' ')}: {error}"
            return f"{tool_name.replace('_', ' ')} failed"

        if tool_name == "project_edit_file":
            path = _clean_text(args.get("path") or result.get("path"), max_chars=52)
            if path:
                return f"Updated {_compact_path(path)}"
        if tool_name == "build_run":
            return "Build started and being tracked"
        if tool_name == "build_logs_search":
            return "Build logs loaded for review"
        if tool_name == "parts_install" and result.get("created_package"):
            identifier = _clean_text(result.get("identifier"), max_chars=30)
            if identifier:
                return f"Created local package {identifier}"
            return "Created a reusable local package"
        if tool_name == "package_create_local":
            identifier = _clean_text(result.get("identifier"), max_chars=30)
            if identifier:
                return f"Created package {identifier}"
            return "Created a local package scaffold"
        if tool_name == "workspace_list_targets":
            total = result.get("total_targets")
            if isinstance(total, int) and total > 0:
                return f"Found {total} build targets in the workspace"
            return "Workspace targets loaded"
        message = _clean_text(result.get("message"), max_chars=68)
        if message:
            return message
        return self._summarize_tool_start(tool_name, args)

    def _should_use_model(self, state: SummaryState, fallback: str) -> bool:
        if not self._config.api_key:
            return False
        now = time.time()
        if fallback == state.latest_summary:
            return False
        return (
            now - state.last_model_at
        ) >= self._config.activity_summary_min_interval_s

    async def _rewrite_with_model(
        self,
        *,
        project_root: str,
        payload: dict[str, Any],
        state: SummaryState,
        fallback: str,
    ) -> str | None:
        try:
            client = self._get_client()
            instructions = self._get_skill_text()
            model_input = self._build_model_input(
                project_root=project_root,
                payload=payload,
                state=state,
                fallback=fallback,
            )
            response = await client.responses.create(
                model=self._config.summary_model,
                instructions=instructions,
                input=model_input,
                max_output_tokens=32,
                truncation="disabled",
            )
            response_dict = _response_model_to_dict(response)
            text = trim_single_line(_extract_text(response_dict), 96)
            if not text:
                return None
            return text
        except Exception:
            log.debug("Activity summary rewrite failed", exc_info=True)
            return None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self._config.api_key,
                base_url=self._config.base_url,
                timeout=self._config.summary_timeout_s,
            )
        return self._client

    def _get_skill_text(self) -> str:
        if self._skill_text is not None:
            return self._skill_text
        skill_path = self._config.skills_dir / "agent-summary" / "SKILL.md"
        try:
            self._skill_text = skill_path.read_text(encoding="utf-8")
        except Exception:
            self._skill_text = (
                "Return one short live progress line from the provided events. "
                "No speculation. No first person. 6-16 words preferred."
            )
        return self._skill_text

    def _build_model_input(
        self,
        *,
        project_root: str,
        payload: dict[str, Any],
        state: SummaryState,
        fallback: str,
    ) -> str:
        phase = payload.get("phase")
        recent_events = [
            {
                "kind": event.kind,
                "label": event.label,
                "detail": event.detail,
            }
            for event in state.events[-self._config.activity_summary_max_events :]
        ]
        data = {
            "project": Path(project_root).name,
            "phase": phase,
            "fallback_summary": fallback,
            "latest_preamble": state.latest_preamble,
            "recent_events": recent_events,
        }
        return json.dumps(data, ensure_ascii=False)
