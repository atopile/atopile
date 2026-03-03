"""Append-only conversation log for debugging and fine-tuning."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LogEvent:
    timestamp: float
    event_type: str
    data: dict[str, Any]


@dataclass
class ConversationLog:
    run_id: str
    session_id: str
    events: list[LogEvent] = field(default_factory=list)

    def record(self, event_type: str, **data: Any) -> None:
        self.events.append(
            LogEvent(
                timestamp=time.time(),
                event_type=event_type,
                data=data,
            )
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for event in self.events:
                record = {
                    "ts": event.timestamp,
                    "run_id": self.run_id,
                    "session_id": self.session_id,
                    "event": event.event_type,
                    **event.data,
                }
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
