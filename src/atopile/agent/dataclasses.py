"""Shared dataclasses for agent runtime state."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SummaryEvent:
    ts: float
    kind: str
    label: str
    detail: str | None = None


@dataclass
class SummaryState:
    events: list[SummaryEvent] = field(default_factory=list)
    latest_preamble: str | None = None
    latest_summary: str | None = None
    latest_fallback: str | None = None
    last_model_at: float = 0.0
    last_phase: str | None = None


@dataclass
class ChecklistItem:
    id: str
    description: str
    criteria: str
    status: str = "not_started"
    requirement_id: str | None = None
    source: str | None = None
    message_id: str | None = None
    justification: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChecklistItem:
        return cls(
            id=str(data["id"]),
            description=str(data["description"]),
            criteria=str(data["criteria"]),
            status=str(data.get("status", "not_started")),
            requirement_id=(
                str(data["requirement_id"])
                if data.get("requirement_id") is not None
                else None
            ),
            source=str(data["source"]) if data.get("source") is not None else None,
            message_id=(
                str(data["message_id"]) if data.get("message_id") is not None else None
            ),
            justification=(
                str(data["justification"])
                if data.get("justification") is not None
                else None
            ),
        )


@dataclass
class Checklist:
    items: list[ChecklistItem] = field(default_factory=list)
    created_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Checklist:
        raw_items = data.get("items", [])
        items = [
            ChecklistItem.from_dict(item)
            for item in raw_items
            if isinstance(item, dict)
        ]
        return cls(items=items, created_at=float(data.get("created_at", 0.0)))

    def save_to_skill_state(self, skill_state: dict[str, Any]) -> None:
        skill_state["checklist"] = self.to_dict()

    @classmethod
    def from_skill_state(cls, skill_state: dict[str, Any]) -> Checklist | None:
        data = skill_state.get("checklist")
        if not isinstance(data, dict):
            return None
        return cls.from_dict(data)
