"""Message log — persistent tracking for user/steering messages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# Message status constants
MSG_PENDING = "pending"
MSG_ACKNOWLEDGED = "acknowledged"
MSG_ACTIVE = "active"
MSG_DONE = "done"

_TERMINAL_ITEM_STATUSES = frozenset({"done", "blocked"})


@dataclass
class TrackedMessage:
    message_id: str
    session_id: str
    project_root: str
    role: str  # "user" or "steering"
    content: str
    status: str  # pending | acknowledged | active | done
    justification: str | None = None
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "project_root": self.project_root,
            "role": self.role,
            "content": self.content,
            "status": self.status,
            "justification": self.justification,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrackedMessage:
        return cls(
            message_id=str(data["message_id"]),
            session_id=str(data["session_id"]),
            project_root=str(data["project_root"]),
            role=str(data["role"]),
            content=str(data["content"]),
            status=str(data.get("status", MSG_PENDING)),
            justification=data.get("justification"),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
        )


@dataclass
class TrackedChecklistItem:
    item_id: str
    session_id: str
    message_id: str | None = None
    description: str = ""
    criteria: str = ""
    status: str = "not_started"
    requirement_id: str | None = None
    source: str | None = None
    justification: str | None = None
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "item_id": self.item_id,
            "session_id": self.session_id,
            "description": self.description,
            "criteria": self.criteria,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.message_id is not None:
            d["message_id"] = self.message_id
        if self.requirement_id is not None:
            d["requirement_id"] = self.requirement_id
        if self.source is not None:
            d["source"] = self.source
        if self.justification is not None:
            d["justification"] = self.justification
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TrackedChecklistItem:
        return cls(
            item_id=str(data["item_id"]),
            session_id=str(data["session_id"]),
            message_id=data.get("message_id"),
            description=str(data.get("description", "")),
            criteria=str(data.get("criteria", "")),
            status=str(data.get("status", "not_started")),
            requirement_id=data.get("requirement_id"),
            source=data.get("source"),
            justification=data.get("justification"),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
        )


def build_pending_message_nudge(messages: list[TrackedMessage]) -> str:
    """Build a nudge prompt for unaddressed messages."""
    lines = [
        "You have unaddressed messages that need attention. For each message, either:",
        "- Create checklist items linked via `message_id`, or",
        "- Call `message_acknowledge` with a justification.",
        "",
    ]
    for msg in messages:
        role_tag = f"[{msg.role}]" if msg.role != "user" else ""
        prefix = f"  message_id={msg.message_id} {role_tag}".strip()
        # Show a preview of the content (first 200 chars)
        preview = msg.content[:200]
        if len(msg.content) > 200:
            preview += "..."
        lines.append(f"{prefix}: {preview}")
    lines.append("")
    lines.append("Address all pending messages before continuing.")
    return "\n".join(lines)
