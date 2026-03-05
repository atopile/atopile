"""Agent configuration — pure data, zero runtime dependencies."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


def _env_int(
    key: str, default: str, *, lo: int | None = None, hi: int | None = None
) -> int:
    v = int(_env(key, default))
    if lo is not None:
        v = max(lo, v)
    if hi is not None:
        v = min(hi, v)
    return v


def _env_float(
    key: str, default: str, *, lo: float | None = None, hi: float | None = None
) -> float:
    v = float(_env(key, default))
    if lo is not None:
        v = max(lo, v)
    if hi is not None:
        v = min(hi, v)
    return v


_TRACE_DISABLE_VALUES = {"0", "false", "no", "off"}


@dataclass
class AgentConfig:
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-5.4"
    api_key: str | None = None
    timeout_s: float = 120.0
    max_tool_loops: int = 240
    max_turn_seconds: float = 7_200.0
    api_retries: int = 4
    api_retry_base_delay_s: float = 0.5
    api_retry_max_delay_s: float = 8.0
    skills_dir: Path = field(
        default_factory=lambda: (
            Path(__file__).resolve().parents[4] / ".claude" / "skills"
        )
    )
    fixed_skill_ids: list[str] = field(default_factory=lambda: ["agent", "ato", "planning"])
    fixed_skill_token_budgets: dict[str, int] = field(default_factory=dict)
    fixed_skill_chars_per_token: float = 4.0
    fixed_skill_total_max_chars: int = 220_000
    prefix_max_chars: int = 220_000
    context_summary_max_chars: int = 8_000
    user_message_max_chars: int = 12_000
    tool_output_max_chars: int = 10_000
    context_hard_max_tokens: int = 1_000_000
    prompt_cache_retention: str = "24h"
    max_checklist_continuations: int = 25
    silent_retry_max: int = 2
    trace_enabled: bool = True
    trace_preview_max_chars: int = 4_000

    @classmethod
    def from_env(cls) -> AgentConfig:
        from atopile.server.agent.orchestrator_helpers import (
            _parse_fixed_skill_token_budgets,
        )

        # Load .env from the project root (if present) so API keys are available
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

        fixed_skill_ids = ["agent", "ato", "planning"]
        return cls(
            base_url=_env("ATOPILE_AGENT_BASE_URL", "https://api.openai.com/v1"),
            model=_env("ATOPILE_AGENT_MODEL", "gpt-5.4"),
            api_key=os.getenv("ATOPILE_AGENT_OPENAI_API_KEY")
            or os.getenv("OPENAI_API_KEY"),
            timeout_s=_env_float("ATOPILE_AGENT_TIMEOUT_S", "120"),
            max_tool_loops=_env_int("ATOPILE_AGENT_MAX_TOOL_LOOPS", "240"),
            max_turn_seconds=_env_float(
                "ATOPILE_AGENT_MAX_TURN_SECONDS", "7200", lo=30.0, hi=7_200.0
            ),
            api_retries=_env_int("ATOPILE_AGENT_API_RETRIES", "4"),
            api_retry_base_delay_s=_env_float(
                "ATOPILE_AGENT_API_RETRY_BASE_DELAY_S", "0.5"
            ),
            api_retry_max_delay_s=_env_float(
                "ATOPILE_AGENT_API_RETRY_MAX_DELAY_S", "8.0"
            ),
            fixed_skill_ids=fixed_skill_ids,
            fixed_skill_token_budgets=_parse_fixed_skill_token_budgets(
                _env(
                    "ATOPILE_AGENT_FIXED_SKILL_TOKEN_BUDGETS", "agent:10000,ato:40000,planning:5000"
                ),
                default_skill_ids=fixed_skill_ids,
            ),
            fixed_skill_chars_per_token=_env_float(
                "ATOPILE_AGENT_FIXED_SKILL_CHARS_PER_TOKEN", "4.0", lo=1.0, hi=8.0
            ),
            fixed_skill_total_max_chars=_env_int(
                "ATOPILE_AGENT_FIXED_SKILL_TOTAL_MAX_CHARS", "220000"
            ),
            prefix_max_chars=_env_int("ATOPILE_AGENT_PREFIX_MAX_CHARS", "220000"),
            context_summary_max_chars=_env_int(
                "ATOPILE_AGENT_CONTEXT_SUMMARY_MAX_CHARS", "8000"
            ),
            user_message_max_chars=_env_int(
                "ATOPILE_AGENT_USER_MESSAGE_MAX_CHARS", "12000"
            ),
            tool_output_max_chars=_env_int(
                "ATOPILE_AGENT_TOOL_OUTPUT_MAX_CHARS", "10000"
            ),
            context_hard_max_tokens=_env_int(
                "ATOPILE_AGENT_CONTEXT_HARD_MAX_TOKENS", "1000000"
            ),
            max_checklist_continuations=_env_int(
                "ATOPILE_AGENT_MAX_CHECKLIST_CONTINUATIONS", "50", lo=0, hi=200
            ),
            silent_retry_max=_env_int(
                "ATOPILE_AGENT_SILENT_RETRY_MAX", "2", lo=0, hi=5
            ),
            prompt_cache_retention=_env("ATOPILE_AGENT_PROMPT_CACHE_RETENTION", "24h"),
            trace_enabled=_env("ATOPILE_AGENT_TRACE_ENABLED", "1").strip().lower()
            not in _TRACE_DISABLE_VALUES,
            trace_preview_max_chars=_env_int(
                "ATOPILE_AGENT_TRACE_PREVIEW_MAX_CHARS", "4000", lo=300, hi=20000
            ),
        )
