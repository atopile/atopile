"""Checklist — structured task tracking for agent continuation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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


@dataclass
class ChecklistItem:
    id: str
    description: str
    criteria: str
    status: str = "not_started"  # not_started | doing | done | blocked
    requirement_id: str | None = (
        None  # Optional link to spec requirement id in docstring
    )
    source: str | None = None  # Optional provenance tag (e.g. "steering")
    message_id: str | None = None  # Optional link to tracked_messages
    justification: str | None = None  # Reason when marking done/blocked

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "description": self.description,
            "criteria": self.criteria,
            "status": self.status,
        }
        if self.requirement_id is not None:
            d["requirement_id"] = self.requirement_id
        if self.source is not None:
            d["source"] = self.source
        if self.message_id is not None:
            d["message_id"] = self.message_id
        if self.justification is not None:
            d["justification"] = self.justification
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChecklistItem:
        return cls(
            id=str(data["id"]),
            description=str(data["description"]),
            criteria=str(data["criteria"]),
            status=str(data.get("status", "not_started")),
            requirement_id=data.get("requirement_id"),
            source=data.get("source"),
            message_id=data.get("message_id"),
            justification=data.get("justification"),
        )


@dataclass
class Checklist:
    items: list[ChecklistItem] = field(default_factory=list)
    created_at: float = 0.0

    def incomplete_items(self) -> list[ChecklistItem]:
        return [i for i in self.items if i.status in ("not_started", "doing")]

    def all_terminal(self) -> bool:
        return all(i.status in ("done", "blocked") for i in self.items)

    def summary_text(self) -> str:
        lines: list[str] = []
        for item in self.items:
            icon = _STATUS_ICONS.get(item.status, "[ ]")
            req = f" [→{item.requirement_id}]" if item.requirement_id else ""
            src = f" [src:{item.source}]" if item.source else ""
            lines.append(
                f"{icon} {item.id} ({item.status}): {item.description}{req}{src}"
            )
        return "\n".join(lines)

    def continuation_prompt(self) -> str:
        incomplete = self.incomplete_items()
        lines = ["Checklist has incomplete items:"]
        for item in incomplete:
            req = (
                f" (spec requirement {item.requirement_id})"
                if item.requirement_id
                else ""
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [i.to_dict() for i in self.items],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Checklist:
        items = [ChecklistItem.from_dict(i) for i in data.get("items", [])]
        return cls(items=items, created_at=float(data.get("created_at", 0.0)))

    def save_to_skill_state(self, skill_state: dict[str, Any]) -> None:
        skill_state["checklist"] = self.to_dict()

    @classmethod
    def from_skill_state(cls, skill_state: dict[str, Any]) -> Checklist | None:
        data = skill_state.get("checklist")
        if not data or not isinstance(data, dict):
            return None
        return cls.from_dict(data)
