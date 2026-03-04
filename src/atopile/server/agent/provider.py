"""LLM provider — wraps OpenAI Responses API into a clean interface."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI

from atopile.server.agent.config import AgentConfig
from atopile.server.agent.orchestrator_helpers import (
    _build_prompt_cache_key,
    _compute_network_retry_delay_s,
    _compute_rate_limit_retry_delay_s,
    _extract_function_calls,
    _extract_output_phase,
    _extract_sdk_error_text,
    _extract_text,
    _is_context_length_exceeded,
    _payload_has_function_call_outputs,
    _response_model_to_dict,
    _shrink_function_call_outputs_payload,
)

log = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Normalized tool/function call from the LLM."""

    id: str
    name: str
    arguments_raw: str
    arguments: dict[str, Any]


@dataclass
class TokenUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass
class LLMResponse:
    """Normalized response from any LLM provider."""

    id: str | None
    text: str
    tool_calls: list[ToolCall]
    phase: str | None = None  # "commentary" | "final_answer" | None
    usage: TokenUsage | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class LLMProvider(Protocol):
    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        instructions: str,
        tools: list[dict[str, Any]],
        skill_state: dict[str, Any],
        project_path: Any,
        previous_response_id: str | None = None,
    ) -> LLMResponse: ...


class OpenAIProvider:
    """Wraps the OpenAI Responses API."""

    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self._config.api_key,
                base_url=self._config.base_url,
                timeout=self._config.timeout_s,
            )
        return self._client

    def _build_payload(
        self,
        *,
        messages: list[dict[str, Any]],
        instructions: str,
        tools: list[dict[str, Any]],
        skill_state: dict[str, Any],
        project_path: Any,
        previous_response_id: str | None = None,
    ) -> dict[str, Any]:
        from pathlib import Path

        pp = project_path if isinstance(project_path, Path) else Path(str(project_path))
        payload: dict[str, Any] = {
            "model": self._config.model,
            "input": messages,
            "instructions": instructions,
            "tools": tools,
            "tool_choice": "auto",
            "truncation": "disabled",
            "prompt_cache_key": _build_prompt_cache_key(
                project_path=pp,
                tool_defs=tools,
                skill_state=skill_state,
                model=self._config.model,
            ),
            "prompt_cache_retention": self._config.prompt_cache_retention,
        }
        if previous_response_id:
            payload["previous_response_id"] = previous_response_id
        return payload

    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        instructions: str,
        tools: list[dict[str, Any]],
        skill_state: dict[str, Any],
        project_path: Any,
        previous_response_id: str | None = None,
    ) -> LLMResponse:
        payload = self._build_payload(
            messages=messages,
            instructions=instructions,
            tools=tools,
            skill_state=skill_state,
            project_path=project_path,
            previous_response_id=previous_response_id,
        )
        body = await self._request_with_retries(payload)
        return self._normalize_response(body)

    async def _request_with_retries(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        client = self._get_client()
        working_payload = dict(payload)
        compacted_once = False
        function_output_shrink_steps = (5000, 2500, 1200, 600, 300)
        function_output_shrink_index = 0
        cfg = self._config

        for attempt in range(cfg.api_retries + 1):
            try:
                response = await client.responses.create(**working_payload)
                break
            except APIStatusError as exc:
                status_code = getattr(exc, "status_code", "unknown")

                # Rate-limited → retry with backoff
                if status_code == 429 and attempt < cfg.api_retries:
                    delay_s = _compute_rate_limit_retry_delay_s(
                        exc=exc,
                        attempt=attempt,
                        base_delay_s=cfg.api_retry_base_delay_s,
                        max_delay_s=cfg.api_retry_max_delay_s,
                    )
                    await asyncio.sleep(delay_s)
                    continue

                # Context length exceeded → shrink function call outputs
                if _is_context_length_exceeded(
                    exc
                ) and _payload_has_function_call_outputs(working_payload):
                    if function_output_shrink_index < len(
                        function_output_shrink_steps
                    ):
                        max_chars = function_output_shrink_steps[
                            function_output_shrink_index
                        ]
                        function_output_shrink_index += 1
                        reduced = _shrink_function_call_outputs_payload(
                            working_payload, max_chars=max_chars
                        )
                        if reduced is not None:
                            working_payload = reduced
                            continue
                    # Shrink exhausted — fall through to try compaction
                    # before giving up.
                    pass

                # Context length exceeded → try compaction once
                if (
                    _is_context_length_exceeded(exc)
                    and not compacted_once
                    and isinstance(
                        working_payload.get("previous_response_id"), str
                    )
                    and working_payload.get("previous_response_id")
                ):
                    compacted_once = True
                    compacted_id = await self._compact_previous_response(
                        str(working_payload["previous_response_id"])
                    )
                    if compacted_id:
                        working_payload = dict(working_payload)
                        working_payload["previous_response_id"] = compacted_id
                        continue

                # If both shrink and compaction failed, raise
                if _is_context_length_exceeded(exc):
                    raise RuntimeError(
                        "Tool outputs are too large for the model context window."
                    ) from exc

                snippet = _extract_sdk_error_text(exc)[:500]
                raise RuntimeError(
                    f"Model API request failed ({status_code}): {snippet}"
                ) from exc

            except (APIConnectionError, APITimeoutError) as exc:
                if attempt < cfg.api_retries:
                    delay_s = _compute_network_retry_delay_s(
                        attempt=attempt,
                        base_delay_s=cfg.api_retry_base_delay_s,
                        max_delay_s=cfg.api_retry_max_delay_s,
                    )
                    await asyncio.sleep(delay_s)
                    continue
                raise RuntimeError(f"Model API request failed: {exc}") from exc

        body = _response_model_to_dict(response)
        if not isinstance(body, dict):
            raise RuntimeError("Model API returned non-object response")
        return body

    async def _compact_previous_response(
        self, previous_response_id: str
    ) -> str | None:
        client = self._get_client()
        try:
            compacted = await client.responses.compact(
                model=self._config.model,
                previous_response_id=previous_response_id,
            )
        except (APIStatusError, APIConnectionError, APITimeoutError):
            return None
        body = _response_model_to_dict(compacted)
        compacted_id = body.get("id")
        if isinstance(compacted_id, str) and compacted_id:
            return compacted_id
        return None

    async def count_input_tokens(self, payload: dict[str, Any]) -> int | None:
        client = self._get_client()
        count_payload = {
            "model": payload.get("model", self._config.model),
            "input": payload.get("input"),
            "instructions": payload.get("instructions"),
            "previous_response_id": payload.get("previous_response_id"),
            "tools": payload.get("tools"),
            "tool_choice": payload.get("tool_choice"),
            "truncation": payload.get("truncation", "disabled"),
        }
        try:
            counted = await client.responses.input_tokens.count(**count_payload)
        except Exception:
            log.debug("Token count request failed", exc_info=True)
            return None
        body = _response_model_to_dict(counted)
        tokens = body.get("input_tokens")
        if isinstance(tokens, int):
            return tokens
        return None

    @staticmethod
    def _normalize_response(body: dict[str, Any]) -> LLMResponse:
        import json as _json

        response_id = body.get("id")
        if response_id is not None:
            response_id = str(response_id)

        text = _extract_text(body)
        raw_calls = _extract_function_calls(body)
        tool_calls: list[ToolCall] = []
        for call in raw_calls:
            call_id = call.get("call_id") or call.get("id")
            if not call_id:
                continue
            name = str(call.get("name", ""))
            arguments_raw = str(call.get("arguments", ""))
            try:
                parsed = _json.loads(arguments_raw) if arguments_raw else {}
                if not isinstance(parsed, dict):
                    parsed = {}
            except Exception:
                parsed = {}
            tool_calls.append(
                ToolCall(
                    id=str(call_id),
                    name=name,
                    arguments_raw=arguments_raw,
                    arguments=parsed,
                )
            )

        usage_raw = body.get("usage")
        usage = None
        if isinstance(usage_raw, dict):
            usage = TokenUsage(
                input_tokens=usage_raw.get("input_tokens"),
                output_tokens=usage_raw.get("output_tokens"),
                total_tokens=usage_raw.get("total_tokens"),
            )

        phase = _extract_output_phase(body)

        return LLMResponse(
            id=response_id,
            text=text,
            tool_calls=tool_calls,
            phase=phase,
            usage=usage,
            raw=body,
        )
