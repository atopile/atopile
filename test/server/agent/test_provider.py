from __future__ import annotations

from atopile.server.agent.provider import OpenAIProvider


def test_normalize_response_extracts_reasoning_and_cached_tokens() -> None:
    response = OpenAIProvider._normalize_response(
        {
            "id": "resp_123",
            "output": [],
            "usage": {
                "input_tokens": 1200,
                "output_tokens": 300,
                "total_tokens": 1500,
                "input_tokens_details": {"cached_tokens": 900},
                "output_tokens_details": {"reasoning_tokens": 42},
            },
        }
    )

    assert response.usage is not None
    assert response.usage.input_tokens == 1200
    assert response.usage.output_tokens == 300
    assert response.usage.total_tokens == 1500
    assert response.usage.cached_input_tokens == 900
    assert response.usage.reasoning_tokens == 42
