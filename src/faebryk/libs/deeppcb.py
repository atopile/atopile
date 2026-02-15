from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DeepPCBConfig(BaseSettings):
    """DeepPCB API settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
        case_sensitive=False,
    )

    base_url: str = Field(
        default="https://api.deeppcb.ai",
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_BASE_URL",
            "DEEPPCB_BASE_URL",
            "FBRK_DEEPPCB_BASE_URL",
        ),
    )
    api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ATO_DEEPPCB_API_KEY"),
    )
    upload_path: str = Field(
        default="/api/v1/files/uploads/board-file",
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_UPLOAD_PATH",
            "DEEPPCB_UPLOAD_PATH",
            "FBRK_DEEPPCB_UPLOAD_PATH",
        ),
    )
    layout_path: str = Field(
        default="/api/v1/boards",
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_LAYOUT_PATH",
            "DEEPPCB_LAYOUT_PATH",
            "FBRK_DEEPPCB_LAYOUT_PATH",
        ),
    )
    status_path_template: str = Field(
        default="/api/v1/boards/{task_id}",
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_STATUS_PATH_TEMPLATE",
            "DEEPPCB_STATUS_PATH_TEMPLATE",
            "FBRK_DEEPPCB_STATUS_PATH_TEMPLATE",
        ),
    )
    alt_status_path_template: str = Field(
        default="/api/v1/user/boards/{task_id}",
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_ALT_STATUS_PATH_TEMPLATE",
            "DEEPPCB_ALT_STATUS_PATH_TEMPLATE",
            "FBRK_DEEPPCB_ALT_STATUS_PATH_TEMPLATE",
        ),
    )
    candidates_path_template: str = Field(
        default="/api/v1/boards/{task_id}",
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_CANDIDATES_PATH_TEMPLATE",
            "DEEPPCB_CANDIDATES_PATH_TEMPLATE",
            "FBRK_DEEPPCB_CANDIDATES_PATH_TEMPLATE",
        ),
    )
    download_path_template: str = Field(
        default="/api/v1/boards/{task_id}/revision-artifact",
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_DOWNLOAD_PATH_TEMPLATE",
            "DEEPPCB_DOWNLOAD_PATH_TEMPLATE",
            "FBRK_DEEPPCB_DOWNLOAD_PATH_TEMPLATE",
        ),
    )
    alt_download_path_template: str = Field(
        default="/api/v1/boards/{task_id}/download-artifact",
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_ALT_DOWNLOAD_PATH_TEMPLATE",
            "DEEPPCB_ALT_DOWNLOAD_PATH_TEMPLATE",
            "FBRK_DEEPPCB_ALT_DOWNLOAD_PATH_TEMPLATE",
        ),
    )
    confirm_path_template: str = Field(
        default="/api/v1/boards/{task_id}/confirm",
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_CONFIRM_PATH_TEMPLATE",
            "DEEPPCB_CONFIRM_PATH_TEMPLATE",
            "FBRK_DEEPPCB_CONFIRM_PATH_TEMPLATE",
        ),
    )
    alt_confirm_path_template: str = Field(
        default="/api/v1/user/boards/{task_id}/confirm",
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_ALT_CONFIRM_PATH_TEMPLATE",
            "DEEPPCB_ALT_CONFIRM_PATH_TEMPLATE",
            "FBRK_DEEPPCB_ALT_CONFIRM_PATH_TEMPLATE",
        ),
    )
    resume_path_template: str = Field(
        default="/api/v1/boards/{task_id}/resume",
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_RESUME_PATH_TEMPLATE",
            "DEEPPCB_RESUME_PATH_TEMPLATE",
            "FBRK_DEEPPCB_RESUME_PATH_TEMPLATE",
        ),
    )
    alt_resume_path_template: str = Field(
        default="/api/v1/user/boards/{task_id}/resume",
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_ALT_RESUME_PATH_TEMPLATE",
            "DEEPPCB_ALT_RESUME_PATH_TEMPLATE",
            "FBRK_DEEPPCB_ALT_RESUME_PATH_TEMPLATE",
        ),
    )
    check_constraints_path: str = Field(
        default="/api/v1/boards/check-constraints",
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_CHECK_CONSTRAINTS_PATH",
            "DEEPPCB_CHECK_CONSTRAINTS_PATH",
            "FBRK_DEEPPCB_CHECK_CONSTRAINTS_PATH",
        ),
    )
    request_lookup_path_template: str = Field(
        default="/api/v1/boards/requests/{request_id}",
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_REQUEST_LOOKUP_PATH_TEMPLATE",
            "DEEPPCB_REQUEST_LOOKUP_PATH_TEMPLATE",
            "FBRK_DEEPPCB_REQUEST_LOOKUP_PATH_TEMPLATE",
        ),
    )
    cancel_path_template: str = Field(
        default="/api/v1/boards/{task_id}/stop",
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_CANCEL_PATH_TEMPLATE",
            "DEEPPCB_CANCEL_PATH_TEMPLATE",
            "FBRK_DEEPPCB_CANCEL_PATH_TEMPLATE",
        ),
    )
    alt_cancel_path_template: str = Field(
        default="/api/v1/boards/{task_id}/workflow/stop",
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_ALT_CANCEL_PATH_TEMPLATE",
            "DEEPPCB_ALT_CANCEL_PATH_TEMPLATE",
            "FBRK_DEEPPCB_ALT_CANCEL_PATH_TEMPLATE",
        ),
    )
    timeout_s: float = Field(
        default=60.0,
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_TIMEOUT_S",
            "DEEPPCB_TIMEOUT_S",
            "FBRK_DEEPPCB_TIMEOUT_S",
        ),
    )
    confirm_retries: int = Field(
        default=8,
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_CONFIRM_RETRIES",
            "DEEPPCB_CONFIRM_RETRIES",
            "FBRK_DEEPPCB_CONFIRM_RETRIES",
        ),
    )
    confirm_retry_delay_s: float = Field(
        default=1.5,
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_CONFIRM_RETRY_DELAY_S",
            "DEEPPCB_CONFIRM_RETRY_DELAY_S",
            "FBRK_DEEPPCB_CONFIRM_RETRY_DELAY_S",
        ),
    )
    board_ready_timeout_s: float = Field(
        default=90.0,
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_BOARD_READY_TIMEOUT_S",
            "DEEPPCB_BOARD_READY_TIMEOUT_S",
            "FBRK_DEEPPCB_BOARD_READY_TIMEOUT_S",
        ),
    )
    board_ready_poll_s: float = Field(
        default=2.0,
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_BOARD_READY_POLL_S",
            "DEEPPCB_BOARD_READY_POLL_S",
            "FBRK_DEEPPCB_BOARD_READY_POLL_S",
        ),
    )
    bearer_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_BEARER_TOKEN",
            "DEEPPCB_BEARER_TOKEN",
            "FBRK_DEEPPCB_BEARER_TOKEN",
        ),
    )
    webhook_url: str | None = Field(
        default="https://example.com/deeppcb-autolayout",
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_WEBHOOK_URL",
            "DEEPPCB_WEBHOOK_URL",
            "FBRK_DEEPPCB_WEBHOOK_URL",
        ),
    )
    webhook_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "ATO_DEEPPCB_WEBHOOK_TOKEN",
            "DEEPPCB_WEBHOOK_TOKEN",
            "FBRK_DEEPPCB_WEBHOOK_TOKEN",
        ),
    )

    @field_validator("bearer_token", "webhook_url", "webhook_token", mode="before")
    @classmethod
    def _blank_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @classmethod
    def from_env(cls) -> "DeepPCBConfig":
        return cls()


class DeepPCBApiClient:
    """HTTP client wrapper for DeepPCB API calls."""

    def __init__(self, config: DeepPCBConfig | None = None) -> None:
        self.config = config or DeepPCBConfig.from_env()

    def auth_headers(self) -> dict[str, str]:
        headers = {"x-deeppcb-api-key": self.config.api_key}
        bearer_token = (self.config.bearer_token or "").strip()
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
        return headers

    def request_json(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = self.request_payload(method, path, json_body=json_body)
        if not isinstance(payload, dict):
            raise RuntimeError(f"DeepPCB JSON response was not an object: {payload!r}")
        return payload

    def request_payload(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        form_data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        is_absolute_url: bool = False,
        include_auth_headers: bool = True,
    ) -> Any:
        response = self.request_raw(
            method=method,
            path=path,
            json_body=json_body,
            form_data=form_data,
            files=files,
            params=params,
            headers=headers,
            is_absolute_url=is_absolute_url,
            include_auth_headers=include_auth_headers,
        )
        return _parse_json_or_text(response.text)

    def request_raw(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        form_data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        is_absolute_url: bool = False,
        include_auth_headers: bool = True,
    ) -> httpx.Response:
        request_headers: dict[str, str] = {}
        if include_auth_headers:
            request_headers.update(self.auth_headers())
        if headers:
            request_headers.update(headers)

        url = path if is_absolute_url else _join_url(self.config.base_url, path)
        with httpx.Client(
            timeout=self.config.timeout_s,
            follow_redirects=True,
        ) as client:
            try:
                response = client.request(
                    method,
                    url,
                    json=json_body,
                    data=form_data,
                    files=files,
                    params=params,
                    headers=request_headers,
                )
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                detail = exc.response.text.strip()
                detail = detail[:2_000] if detail else "<no response body>"
                detail = _redact_sensitive_values(
                    detail,
                    (
                        self.config.api_key,
                        self.config.bearer_token,
                        self.config.webhook_token,
                    ),
                )
                raise RuntimeError(
                    f"DeepPCB API request failed ({method} {url}) with status "
                    f"{status}. Response: {detail}"
                ) from exc

    def upload_board_file(self, board_path: Path) -> str:
        with board_path.open("rb") as file_obj:
            files = {
                "inputFile": (
                    board_path.name,
                    file_obj,
                    _guess_content_type(board_path),
                )
            }
            payload = self.request_payload(
                "POST",
                self.config.upload_path,
                files=files,
                headers={"accept": "text/plain"},
            )

        upload_url = _extract_string(
            payload,
            keys=("url", "fileUrl", "file_url", "storageUrl", "value"),
        )
        if not upload_url:
            if isinstance(payload, str) and payload.strip():
                upload_url = payload.strip()
            else:
                raise RuntimeError(
                    "DeepPCB upload response missing file URL. "
                    f"Payload: {_pretty_json(payload)}"
                )
        return upload_url


def _walk(payload: Any):
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield (key, value)
            yield from _walk(value)
    elif isinstance(payload, list):
        for value in payload:
            yield from _walk(value)


def _extract_string(payload: Any, keys: tuple[str, ...]) -> str | None:
    lookup = {key.lower() for key in keys}
    for value in _walk(payload):
        if not isinstance(value, tuple) or len(value) != 2:
            continue
        key, raw = value
        if key.lower() not in lookup:
            continue
        if raw is None:
            continue
        if isinstance(raw, (int, float)):
            return str(raw)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return None


def _guess_content_type(path: Path) -> str:
    if path.suffix == ".kicad_pcb":
        return "application/octet-stream"
    if path.suffix in {".json", ".deeppcb"}:
        return "application/json"
    if path.suffix in {".dsn", ".ses"}:
        return "text/plain"
    return "application/octet-stream"


def _extract_top_level_value(
    payload: dict[str, Any],
    keys: tuple[str, ...],
) -> str | None:
    lookup = {key.lower() for key in keys}
    for key, value in payload.items():
        if key.lower() not in lookup:
            continue
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_board_candidates(payload: Any) -> list[str]:
    candidates: list[str] = []

    def add(value: Any) -> None:
        if isinstance(value, (int, float)):
            token = str(value)
        elif isinstance(value, str):
            token = value.strip().strip('"')
        else:
            return

        if not token:
            return
        if token not in candidates:
            candidates.append(token)

    if isinstance(payload, str):
        add(payload)
        return candidates

    if isinstance(payload, dict):
        top_specific = _extract_top_level_value(
            payload,
            keys=("board_id", "boardId", "boardPId", "boardPublicId", "publicId"),
        )
        if top_specific:
            add(top_specific)

    preferred_keys = {
        "board_id",
        "boardid",
        "boardpid",
        "boardpublicid",
        "publicid",
    }

    for key, value in _walk(payload):
        if key.lower() in preferred_keys:
            add(value)

    if not candidates and isinstance(payload, dict):
        top_id = _extract_top_level_value(payload, keys=("id",))
        if top_id:
            add(top_id)

    return candidates


def _join_url(base_url: str, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _parse_json_or_text(text: str) -> Any:
    stripped = text.strip()
    if not stripped:
        return {}
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return stripped


def _pretty_json(payload: Any) -> str:
    try:
        return json.dumps(payload, indent=2, sort_keys=True)
    except TypeError:
        return str(payload)


def _redact_sensitive_values(
    text: str,
    values: tuple[str | None, ...],
) -> str:
    if not text:
        return text

    output = text
    for raw in values:
        if not isinstance(raw, str):
            continue
        token = raw.strip()
        if len(token) < 4:
            continue
        output = output.replace(token, "***REDACTED***")
    return output
