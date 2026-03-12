"""Circuit breaker — detect identical failing tool calls."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


def _call_signature(tool_name: str, args: dict[str, Any]) -> str:
    try:
        serialized = json.dumps(args, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:
        serialized = str(args)
    raw = f"{tool_name}:{serialized[:600]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


@dataclass
class CircuitBreaker:
    max_identical_failures: int = 2
    _recent_failures: list[str] = field(default_factory=list)

    def record_failure(
        self, tool_name: str, args: dict[str, Any], error: str
    ) -> str | None:
        """Returns a NON-RETRYABLE message if circuit broken, else None."""
        sig = _call_signature(tool_name, args)
        self._recent_failures.append(sig)
        # Keep a bounded window
        if len(self._recent_failures) > 20:
            self._recent_failures = self._recent_failures[-20:]
        # Count consecutive identical failures at the tail
        count = 0
        for past_sig in reversed(self._recent_failures):
            if past_sig == sig:
                count += 1
            else:
                break
        if count >= self.max_identical_failures:
            return (
                f"Circuit breaker tripped: tool '{tool_name}' failed "
                f"{count} times with identical arguments. "
                "Do NOT retry the same call — change your approach or arguments."
            )
        return None

    def record_success(self) -> None:
        """Reset failure tracking on success."""
        self._recent_failures.clear()
