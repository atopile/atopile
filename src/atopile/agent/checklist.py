"""Checklist helpers and transitions for agent continuation."""

from __future__ import annotations

from atopile.agent.dataclasses import Checklist, ChecklistItem

VALID_TRANSITIONS: dict[str, set[str]] = {
    "not_started": {"doing"},
    "doing": {"done", "blocked"},
    "done": set(),  # terminal
    "blocked": {"doing"},  # only via between-turn reset
}

_STATUS_ICONS = {
    "not_started": "[ ]",
    "doing": "[~]",
    "done": "[x]",
    "blocked": "[!]",
}


def _incomplete_items(self: Checklist) -> list[ChecklistItem]:
    return [item for item in self.items if item.status in ("not_started", "doing")]


def _all_terminal(self: Checklist) -> bool:
    return all(item.status in ("done", "blocked") for item in self.items)


def _summary_text(self: Checklist) -> str:
    lines: list[str] = []
    for item in self.items:
        icon = _STATUS_ICONS.get(item.status, "[ ]")
        req = f" [→{item.requirement_id}]" if item.requirement_id else ""
        src = f" [src:{item.source}]" if item.source else ""
        lines.append(f"{icon} {item.id} ({item.status}): {item.description}{req}{src}")
    return "\n".join(lines)


def _continuation_prompt(self: Checklist) -> str:
    incomplete = self.incomplete_items()
    lines = ["Checklist has incomplete items:"]
    for item in incomplete:
        req = (
            f" (spec requirement {item.requirement_id})" if item.requirement_id else ""
        )
        lines.append(f"- {item.id} ({item.status}): {item.description}{req}")
    lines.append("")
    lines.append(
        f"{len(incomplete)} item{'s' if len(incomplete) != 1 else ''} remaining. "
        "Continue with the next item."
    )
    lines.append(
        "All tools are available. Call checklist_update with the numeric "
        "item_id shown in the checklist to mark the next item as 'doing', "
        "then use project_read_file / project_edit_file / build_run / etc. "
        "to implement it."
    )
    return "\n".join(lines)


Checklist.incomplete_items = _incomplete_items
Checklist.all_terminal = _all_terminal
Checklist.summary_text = _summary_text
Checklist.continuation_prompt = _continuation_prompt

__all__ = ["Checklist", "ChecklistItem", "VALID_TRANSITIONS"]
