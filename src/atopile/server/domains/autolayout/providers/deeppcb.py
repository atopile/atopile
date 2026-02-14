"""DeepPCB provider adapter.

This adapter is intentionally tolerant to response shape changes because the
public docs/API payload examples are evolving.
"""

from __future__ import annotations

import json
import os
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from atopile.server.domains.autolayout.models import (
    AutolayoutCandidate,
    AutolayoutState,
    DownloadResult,
    ProviderCapabilities,
    ProviderStatus,
    SubmitRequest,
    SubmitResult,
)
from atopile.server.domains.autolayout.providers.base import AutolayoutProvider
from faebryk.libs.util import ConfigFlagFloat, ConfigFlagString

_DEEPPCB_BASE_URL = ConfigFlagString(
    "DEEPPCB_BASE_URL", "https://api.deeppcb.ai", "Base URL for DeepPCB API"
)
_DEEPPCB_API_KEY = ConfigFlagString("DEEPPCB_API_KEY", "", "API key for DeepPCB API")
_DEEPPCB_UPLOAD_PATH = ConfigFlagString(
    "DEEPPCB_UPLOAD_PATH",
    "/api/v1/files/uploads/board-file",
    "Upload endpoint path",
)
_DEEPPCB_LAYOUT_PATH = ConfigFlagString(
    "DEEPPCB_LAYOUT_PATH", "/api/v1/boards", "Board create endpoint"
)
_DEEPPCB_STATUS_PATH_TEMPLATE = ConfigFlagString(
    "DEEPPCB_STATUS_PATH_TEMPLATE",
    "/api/v1/boards/{task_id}",
    "Board status endpoint template",
)
_DEEPPCB_ALT_STATUS_PATH_TEMPLATE = ConfigFlagString(
    "DEEPPCB_ALT_STATUS_PATH_TEMPLATE",
    "/api/v1/user/boards/{task_id}",
    "Alternate board status endpoint template",
)
_DEEPPCB_CANDIDATES_PATH_TEMPLATE = ConfigFlagString(
    "DEEPPCB_CANDIDATES_PATH_TEMPLATE",
    "/api/v1/boards/{task_id}",
    "Board candidate listing endpoint template",
)
_DEEPPCB_DOWNLOAD_PATH_TEMPLATE = ConfigFlagString(
    "DEEPPCB_DOWNLOAD_PATH_TEMPLATE",
    "/api/v1/boards/{task_id}/revision-artifact",
    "Revision download endpoint template",
)
_DEEPPCB_ALT_DOWNLOAD_PATH_TEMPLATE = ConfigFlagString(
    "DEEPPCB_ALT_DOWNLOAD_PATH_TEMPLATE",
    "/api/v1/boards/{task_id}/download-artifact",
    "Alternate artifact download endpoint template",
)
_DEEPPCB_CONFIRM_PATH_TEMPLATE = ConfigFlagString(
    "DEEPPCB_CONFIRM_PATH_TEMPLATE",
    "/api/v1/boards/{task_id}/confirm",
    "Board confirm endpoint template",
)
_DEEPPCB_ALT_CONFIRM_PATH_TEMPLATE = ConfigFlagString(
    "DEEPPCB_ALT_CONFIRM_PATH_TEMPLATE",
    "/api/v1/user/boards/{task_id}/confirm",
    "Alternate board confirm endpoint template",
)
_DEEPPCB_RESUME_PATH_TEMPLATE = ConfigFlagString(
    "DEEPPCB_RESUME_PATH_TEMPLATE",
    "/api/v1/boards/{task_id}/resume",
    "Board resume endpoint template",
)
_DEEPPCB_ALT_RESUME_PATH_TEMPLATE = ConfigFlagString(
    "DEEPPCB_ALT_RESUME_PATH_TEMPLATE",
    "/api/v1/user/boards/{task_id}/resume",
    "Alternate board resume endpoint template",
)
_DEEPPCB_CHECK_CONSTRAINTS_PATH = ConfigFlagString(
    "DEEPPCB_CHECK_CONSTRAINTS_PATH",
    "/api/v1/boards/check-constraints",
    "Constraints validation endpoint path",
)
_DEEPPCB_REQUEST_LOOKUP_PATH_TEMPLATE = ConfigFlagString(
    "DEEPPCB_REQUEST_LOOKUP_PATH_TEMPLATE",
    "/api/v1/boards/requests/{request_id}",
    "Board lookup by requestId endpoint template",
)
_DEEPPCB_CANCEL_PATH_TEMPLATE = ConfigFlagString(
    "DEEPPCB_CANCEL_PATH_TEMPLATE",
    "/api/v1/boards/{task_id}/stop",
    "Board stop endpoint template",
)
_DEEPPCB_ALT_CANCEL_PATH_TEMPLATE = ConfigFlagString(
    "DEEPPCB_ALT_CANCEL_PATH_TEMPLATE",
    "/api/v1/boards/{task_id}/workflow/stop",
    "Alternate board stop endpoint template",
)
_DEEPPCB_TIMEOUT_S = ConfigFlagFloat(
    "DEEPPCB_TIMEOUT_S", 60.0, "Timeout in seconds for DeepPCB HTTP requests"
)
_DEEPPCB_CONFIRM_RETRIES = ConfigFlagFloat(
    "DEEPPCB_CONFIRM_RETRIES",
    8,
    "Number of confirm retries when board is not yet visible",
)
_DEEPPCB_CONFIRM_RETRY_DELAY_S = ConfigFlagFloat(
    "DEEPPCB_CONFIRM_RETRY_DELAY_S",
    1.5,
    "Delay between confirm retries in seconds",
)
_DEEPPCB_BOARD_READY_TIMEOUT_S = ConfigFlagFloat(
    "DEEPPCB_BOARD_READY_TIMEOUT_S",
    90.0,
    "Max time to wait for board creation to become visible before confirm",
)
_DEEPPCB_BOARD_READY_POLL_S = ConfigFlagFloat(
    "DEEPPCB_BOARD_READY_POLL_S",
    2.0,
    "Polling interval while waiting for board creation visibility",
)
_DEEPPCB_BEARER_TOKEN = ConfigFlagString(
    "DEEPPCB_BEARER_TOKEN",
    "",
    "Optional bearer token for DeepPCB API if your account requires it",
)
_DEEPPCB_WEBHOOK_URL = ConfigFlagString(
    "DEEPPCB_WEBHOOK_URL",
    "https://example.com/deeppcb-autolayout",
    "Webhook URL required by DeepPCB board creation",
)
_DEEPPCB_WEBHOOK_TOKEN = ConfigFlagString(
    "DEEPPCB_WEBHOOK_TOKEN",
    "",
    "Optional webhook token sent to DeepPCB board creation",
)


@dataclass
class DeepPCBConfig:
    base_url: str
    api_key: str
    upload_path: str
    layout_path: str
    status_path_template: str
    alt_status_path_template: str
    candidates_path_template: str
    download_path_template: str
    alt_download_path_template: str
    confirm_path_template: str
    alt_confirm_path_template: str
    resume_path_template: str
    alt_resume_path_template: str
    request_lookup_path_template: str
    cancel_path_template: str
    alt_cancel_path_template: str
    timeout_s: float
    confirm_retries: int = 8
    confirm_retry_delay_s: float = 1.5
    board_ready_timeout_s: float = 90.0
    board_ready_poll_s: float = 2.0
    bearer_token: str | None = None
    webhook_url: str | None = None
    webhook_token: str | None = None

    @classmethod
    def from_env(cls) -> "DeepPCBConfig":
        api_key = (
            os.getenv("ATO_DEEPPCB_API_KEY")
            or os.getenv("DEEPPCB_API_KEY")
            or os.getenv("FBRK_DEEPPCB_API_KEY")
            or _DEEPPCB_API_KEY.get()
        )
        bearer_token = (
            os.getenv("ATO_DEEPPCB_BEARER_TOKEN")
            or os.getenv("DEEPPCB_BEARER_TOKEN")
            or _DEEPPCB_BEARER_TOKEN.get()
            or None
        )
        webhook_url = (
            os.getenv("ATO_DEEPPCB_WEBHOOK_URL")
            or os.getenv("DEEPPCB_WEBHOOK_URL")
            or _DEEPPCB_WEBHOOK_URL.get()
            or None
        )
        webhook_token = (
            os.getenv("ATO_DEEPPCB_WEBHOOK_TOKEN")
            or os.getenv("DEEPPCB_WEBHOOK_TOKEN")
            or _DEEPPCB_WEBHOOK_TOKEN.get()
            or None
        )
        return cls(
            base_url=_DEEPPCB_BASE_URL.get(),
            api_key=api_key,
            upload_path=_DEEPPCB_UPLOAD_PATH.get(),
            layout_path=_DEEPPCB_LAYOUT_PATH.get(),
            status_path_template=_DEEPPCB_STATUS_PATH_TEMPLATE.get(),
            alt_status_path_template=_DEEPPCB_ALT_STATUS_PATH_TEMPLATE.get(),
            candidates_path_template=_DEEPPCB_CANDIDATES_PATH_TEMPLATE.get(),
            download_path_template=_DEEPPCB_DOWNLOAD_PATH_TEMPLATE.get(),
            alt_download_path_template=_DEEPPCB_ALT_DOWNLOAD_PATH_TEMPLATE.get(),
            confirm_path_template=_DEEPPCB_CONFIRM_PATH_TEMPLATE.get(),
            alt_confirm_path_template=_DEEPPCB_ALT_CONFIRM_PATH_TEMPLATE.get(),
            resume_path_template=_DEEPPCB_RESUME_PATH_TEMPLATE.get(),
            alt_resume_path_template=_DEEPPCB_ALT_RESUME_PATH_TEMPLATE.get(),
            request_lookup_path_template=_DEEPPCB_REQUEST_LOOKUP_PATH_TEMPLATE.get(),
            cancel_path_template=_DEEPPCB_CANCEL_PATH_TEMPLATE.get(),
            alt_cancel_path_template=_DEEPPCB_ALT_CANCEL_PATH_TEMPLATE.get(),
            timeout_s=float(_DEEPPCB_TIMEOUT_S.get()),
            confirm_retries=int(float(_DEEPPCB_CONFIRM_RETRIES.get())),
            confirm_retry_delay_s=float(_DEEPPCB_CONFIRM_RETRY_DELAY_S.get()),
            board_ready_timeout_s=float(_DEEPPCB_BOARD_READY_TIMEOUT_S.get()),
            board_ready_poll_s=float(_DEEPPCB_BOARD_READY_POLL_S.get()),
            bearer_token=bearer_token,
            webhook_url=webhook_url,
            webhook_token=webhook_token,
        )


class DeepPCBProvider(AutolayoutProvider):
    """DeepPCB HTTP API adapter."""

    name = "deeppcb"
    capabilities = ProviderCapabilities(
        supports_cancel=True,
        supports_candidates=True,
        supports_download=True,
    )

    def __init__(self, config: DeepPCBConfig | None = None) -> None:
        self.config = config or DeepPCBConfig.from_env()
        self._candidate_cache: dict[str, list[AutolayoutCandidate]] = {}
        self._last_create_payload: Any = None
        self._last_lookup_payload: Any = None

    def submit(self, request: SubmitRequest) -> SubmitResult:
        self._validate_api_key()
        self._inject_constraints_file_url(request)

        resume_board_id = self._resume_board_id(request)
        if resume_board_id:
            if self._resume_stop_first(request):
                try:
                    self.cancel(resume_board_id)
                    self._wait_for_board_not_running(resume_board_id)
                except RuntimeError:
                    # Ignore stop errors and still attempt resume;
                    # board may already be paused/completed.
                    pass
            self._resume_board(resume_board_id, request)
            status = self.status(resume_board_id)
            return SubmitResult(
                external_job_id=resume_board_id,
                state=status.state,
                message=status.message,
                candidates=status.candidates,
            )

        create_reference = self._create_board(request)
        request_refs = [request.job_id, create_reference]
        board_ids = self._resolve_board_ids(request_refs)
        board_id = board_ids[0] if board_ids else create_reference
        board_id = self._wait_for_board_ready(request_refs, board_id)
        self._confirm_board(board_id, request, request_refs=request_refs)

        status = self.status(board_id)
        return SubmitResult(
            external_job_id=board_id,
            state=status.state,
            message=status.message,
            candidates=status.candidates,
        )

    def status(self, external_job_id: str) -> ProviderStatus:
        self._validate_api_key()

        response = None
        status_errors: list[str] = []
        templates = [self.config.status_path_template]
        if self.config.bearer_token:
            templates.append(self.config.alt_status_path_template)
        for template in templates:
            path = template.format(task_id=external_job_id)
            try:
                response = self._request_json("GET", path)
                break
            except RuntimeError as exc:
                status_errors.append(str(exc))

        if response is None:
            raise RuntimeError(
                "DeepPCB status failed for all endpoint variants. "
                + " | ".join(status_errors)
            )

        state = _map_provider_state(
            self._extract_string(
                response,
                keys=("status", "state", "task_status", "boardStatus", "board_state"),
            )
        )

        candidates = self._parse_board_candidates(response, external_job_id)
        if not candidates:
            candidates = self._parse_candidates(response)
            if not candidates:
                candidates = self._candidate_cache.get(external_job_id, [])
        if candidates:
            self._candidate_cache[external_job_id] = candidates

        if candidates and state in {AutolayoutState.RUNNING, AutolayoutState.COMPLETED}:
            state = AutolayoutState.AWAITING_SELECTION

        return ProviderStatus(
            state=state,
            message=self._extract_string(response, keys=("message", "detail")),
            progress=self._extract_progress(response),
            candidates=candidates,
        )

    def list_candidates(self, external_job_id: str) -> list[AutolayoutCandidate]:
        self._validate_api_key()
        status = self.status(external_job_id)
        return status.candidates

    def download_candidate(
        self,
        external_job_id: str,
        candidate_id: str,
        out_dir: Path,
    ) -> DownloadResult:
        self._validate_api_key()
        out_dir.mkdir(parents=True, exist_ok=True)

        candidate = self._candidate_by_id(external_job_id, candidate_id)
        download_url = None
        if candidate is not None:
            download_url = self._extract_string(
                candidate.metadata,
                keys=("fileUrl", "file_url", "download_url", "downloadUrl", "url"),
            )

        if download_url:
            response = self._request_raw(
                "GET",
                download_url,
                is_absolute_url=True,
                include_auth_headers=False,
            )
        else:
            revision = None
            if candidate is not None:
                revision = self._extract_string(
                    candidate.metadata,
                    keys=(
                        "revision",
                        "revisionNumber",
                        "runningNumberOfRevisions",
                        "candidate_id",
                    ),
                )

            params: dict[str, str] = {"type": "JsonFile"}
            if revision:
                params["revision"] = revision

            response = None
            download_errors: list[str] = []
            download_paths = [
                self.config.download_path_template.format(
                    task_id=external_job_id,
                    candidate_id=candidate_id,
                ),
                self.config.alt_download_path_template.format(
                    task_id=external_job_id,
                    candidate_id=candidate_id,
                ),
            ]
            for path in download_paths:
                try:
                    response = self._request_raw("GET", path, params=params)
                    break
                except RuntimeError as exc:
                    download_errors.append(str(exc))

            if response is None:
                raise RuntimeError(
                    "DeepPCB candidate download failed for all endpoint variants. "
                    + " | ".join(download_errors)
                )

        content_type = response.headers.get("content-type", "").lower()

        if "application/json" in content_type:
            payload = _parse_json_or_text(response.text)
            direct_url = self._extract_string(
                payload,
                keys=("url", "download_url", "downloadUrl", "fileUrl"),
            )
            if not direct_url:
                raise RuntimeError(
                    "DeepPCB candidate download response did not include binary "
                    "content nor a download URL"
                )
            response = self._request_raw(
                "GET",
                direct_url,
                is_absolute_url=True,
                include_auth_headers=False,
            )
            content_type = response.headers.get("content-type", "").lower()

        output_path = self._persist_downloaded_layout(
            content=response.content,
            content_type=content_type,
            out_dir=out_dir,
            candidate_id=candidate_id,
        )

        return DownloadResult(
            candidate_id=candidate_id,
            layout_path=output_path,
            files={"kicad_pcb": str(output_path)},
        )

    def cancel(self, external_job_id: str) -> None:
        self._validate_api_key()
        errors: list[str] = []
        for template in (
            self.config.cancel_path_template,
            self.config.alt_cancel_path_template,
        ):
            path = template.format(task_id=external_job_id)
            try:
                self._request_raw("PATCH", path)
                return
            except RuntimeError as exc:
                errors.append(str(exc))

        raise RuntimeError(
            "DeepPCB cancel failed for all endpoint variants. " + " | ".join(errors)
        )

    def _candidate_by_id(
        self,
        external_job_id: str,
        candidate_id: str,
    ) -> AutolayoutCandidate | None:
        for candidate in self.list_candidates(external_job_id):
            if candidate.candidate_id == candidate_id:
                return candidate
        return None

    def _upload_board_file(self, board_path: Path) -> str:
        with board_path.open("rb") as file_obj:
            files = {
                "inputFile": (
                    board_path.name,
                    file_obj,
                    _guess_content_type(board_path),
                )
            }
            payload = self._request_payload(
                "POST",
                self.config.upload_path,
                files=files,
                headers={"accept": "text/plain"},
            )

        upload_url = self._extract_string(
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

    def _create_board(self, request: SubmitRequest) -> str:
        if request.layout_path.suffix.lower() == ".kicad_pcb":
            return self._create_board_kicad(request)

        board_file_url = self._upload_board_file(request.layout_path)
        return self._create_board_from_file_url(request, board_file_url)

    def _create_board_kicad(self, request: SubmitRequest) -> str:
        webhook_url = self._webhook_url(request)
        webhook_token = self._webhook_token(request)
        project_path = self._find_kicad_project_file(request)
        if not project_path:
            raise RuntimeError(
                "DeepPCB KiCad submission requires a .kicad_pro file. "
                "Generate/export the KiCad project first and retry."
            )

        with (
            request.layout_path.open("rb") as board_file_obj,
            project_path.open("rb") as project_file_obj,
        ):
            multipart_fields = {
                "requestId": (None, request.job_id),
                "boardName": (None, f"{request.build_target}-{request.job_id}"),
                "boardInputType": (None, "Kicad"),
                "routingType": (None, self._routing_type(request)),
                "webhookUrl": (None, webhook_url),
                "kicadBoardFile": (
                    request.layout_path.name,
                    board_file_obj,
                    _guess_content_type(request.layout_path),
                ),
                "kicadProjectFile": (
                    project_path.name,
                    project_file_obj,
                    _guess_content_type(project_path),
                ),
            }
            if webhook_token:
                multipart_fields["webhookToken"] = (None, webhook_token)

            payload = self._request_payload(
                "POST",
                self.config.layout_path,
                files=multipart_fields,
                headers={"accept": "text/plain"},
            )

        self._last_create_payload = payload
        return self._extract_board_id(payload)

    def _create_board_from_file_url(
        self,
        request: SubmitRequest,
        board_file_url: str,
    ) -> str:
        webhook_url = self._webhook_url(request)
        webhook_token = self._webhook_token(request)
        data: dict[str, str] = {
            "requestId": request.job_id,
            "boardName": f"{request.build_target}-{request.job_id}",
            "routingType": self._routing_type(request),
            "jsonFileUrl": board_file_url,
            "webhookUrl": webhook_url,
        }
        if webhook_token:
            data["webhookToken"] = webhook_token

        multipart_fields = {key: (None, value) for key, value in data.items() if value}
        try:
            payload = self._request_payload(
                "POST",
                self.config.layout_path,
                files=multipart_fields,
                headers={"accept": "text/plain"},
            )
            self._last_create_payload = payload
            return self._extract_board_id(payload)
        except RuntimeError as exc:
            message = str(exc).lower()
            # Some deployments reject jsonFileUrl for non-json inputs.
            if "jsonfileurl" not in message and "jsonfile" not in message:
                raise
            return self._create_board_with_json_file(request)

    def _create_board_with_json_file(self, request: SubmitRequest) -> str:
        webhook_url = self._webhook_url(request)
        webhook_token = self._webhook_token(request)
        with request.layout_path.open("rb") as file_obj:
            multipart_fields = {
                "requestId": (None, request.job_id),
                "boardName": (None, f"{request.build_target}-{request.job_id}"),
                "routingType": (None, self._routing_type(request)),
                "webhookUrl": (None, webhook_url),
                "jsonFile": (
                    request.layout_path.name,
                    file_obj,
                    _guess_content_type(request.layout_path),
                ),
            }
            if webhook_token:
                multipart_fields["webhookToken"] = (None, webhook_token)
            payload = self._request_payload(
                "POST",
                self.config.layout_path,
                files=multipart_fields,
                headers={"accept": "text/plain"},
            )
        self._last_create_payload = payload
        return self._extract_board_id(payload)

    def _find_kicad_project_file(self, request: SubmitRequest) -> Path | None:
        if request.kicad_project_path and request.kicad_project_path.exists():
            return request.kicad_project_path

        from_layout = request.layout_path.with_suffix(".kicad_pro")
        if from_layout.exists():
            return from_layout

        siblings = sorted(request.layout_path.parent.glob("*.kicad_pro"))
        if siblings:
            return siblings[0]

        return None

    def _extract_board_id(self, payload: Any) -> str:
        candidates = _extract_board_candidates(payload)
        if candidates:
            return candidates[0]
        raise RuntimeError(
            "DeepPCB board create response missing board id. "
            f"Payload: {_pretty_json(payload)}"
        )

    def _confirm_board(
        self,
        board_id: str,
        request: SubmitRequest,
        request_refs: list[str] | None = None,
    ) -> None:
        options = request.options

        timeout = int(options.get("timeout") or options.get("timeout_minutes") or 10)
        max_batch_timeout = int(
            options.get("maxBatchTimeout") or options.get("max_batch_timeout") or 60
        )
        time_to_live = int(
            options.get("timeToLive") or options.get("time_to_live") or 300
        )

        payload: dict[str, Any] = {
            "jobType": self._job_type(request),
            "timeout": timeout,
            "maxBatchTimeout": max_batch_timeout,
            "timeToLive": time_to_live,
        }
        response_board_format = options.get("responseBoardFormat")
        if response_board_format is not None:
            payload["responseBoardFormat"] = response_board_format

        constraints_file_url = options.get("constraintsFileUrl")
        if isinstance(constraints_file_url, str) and constraints_file_url:
            payload["constraintsFileUrl"] = constraints_file_url

        candidate_ids = [board_id]
        if request_refs:
            for resolved in self._resolve_board_ids(request_refs):
                if resolved not in candidate_ids:
                    candidate_ids.insert(0, resolved)

        attempt_variants: list[tuple[str, dict[str, str] | None]] = [
            (self.config.confirm_path_template, None),
        ]
        if self.config.bearer_token:
            attempt_variants.append((self.config.alt_confirm_path_template, None))

        retries = max(1, int(self.config.confirm_retries))
        last_errors: list[str] = []
        for attempt in range(retries):
            errors: list[str] = []
            for candidate_id in candidate_ids:
                for template, override_headers in attempt_variants:
                    path = template.format(task_id=candidate_id)
                    try:
                        headers = {"accept": "*/*"}
                        if override_headers:
                            headers.update(override_headers)
                        self._request_raw(
                            "PATCH",
                            path,
                            json_body=payload,
                            headers=headers,
                        )
                        return
                    except RuntimeError as exc:
                        errors.append(str(exc))

            last_errors = errors
            all_not_found = errors and all(
                "Board.Errors.BoardNotFound" in err for err in errors
            )
            if not all_not_found:
                break

            if request_refs:
                for resolved in self._resolve_board_ids(request_refs):
                    if resolved not in candidate_ids:
                        candidate_ids.insert(0, resolved)

            if attempt < retries - 1:
                time.sleep(max(0.1, self.config.confirm_retry_delay_s))

        raise RuntimeError(
            "DeepPCB confirm failed for all endpoint/id combinations. "
            + " | ".join(last_errors)
            + f" | candidateIds={candidate_ids}"
            + f" | createPayload={_pretty_json(self._last_create_payload)}"
            + f" | lookupPayload={_pretty_json(self._last_lookup_payload)}"
        )

    def _resume_board(self, board_id: str, request: SubmitRequest) -> None:
        options = request.options

        timeout = int(options.get("timeout") or options.get("timeout_minutes") or 10)
        max_batch_timeout = int(
            options.get("maxBatchTimeout") or options.get("max_batch_timeout") or 60
        )
        time_to_live = int(
            options.get("timeToLive") or options.get("time_to_live") or 300
        )

        payload: dict[str, Any] = {
            "jobType": self._job_type(request),
            "timeout": timeout,
            "maxBatchTimeout": max_batch_timeout,
            "timeToLive": time_to_live,
            "routingType": self._routing_type(request),
        }
        response_board_format = options.get("responseBoardFormat")
        if response_board_format is not None:
            payload["responseBoardFormat"] = response_board_format

        constraints_file_url = options.get("constraintsFileUrl")
        if isinstance(constraints_file_url, str) and constraints_file_url:
            payload["constraintsFileUrl"] = constraints_file_url

        attempt_variants: list[tuple[str, dict[str, str] | None]] = [
            (self.config.resume_path_template, None),
        ]
        if self.config.bearer_token:
            attempt_variants.append((self.config.alt_resume_path_template, None))

        errors: list[str] = []
        for template, override_headers in attempt_variants:
            path = template.format(task_id=board_id)
            try:
                headers = {"accept": "*/*"}
                if override_headers:
                    headers.update(override_headers)
                self._request_raw(
                    "PATCH",
                    path,
                    json_body=payload,
                    headers=headers,
                )
                return
            except RuntimeError as exc:
                errors.append(str(exc))

        raise RuntimeError(
            "DeepPCB resume failed for all endpoint variants. " + " | ".join(errors)
        )

    def _resolve_board_ids(self, request_refs: list[str]) -> list[str]:
        results: list[str] = []
        for request_id in request_refs:
            if not request_id:
                continue
            for resolved in self._resolve_board_ids_single(request_id):
                if resolved not in results:
                    results.append(resolved)
        return results

    def _resolve_board_ids_single(self, request_id: str) -> list[str]:
        template = self.config.request_lookup_path_template
        for attempt in range(5):
            try:
                payload = self._request_payload(
                    "GET",
                    template.format(request_id=request_id),
                    headers={"accept": "application/json"},
                )
                self._last_lookup_payload = payload
                candidates = _extract_board_candidates(payload)
                if candidates:
                    return candidates
            except Exception:
                if attempt < 4:
                    time.sleep(0.5)
        return []

    def _wait_for_board_ready(
        self,
        request_refs: list[str],
        initial_board_id: str,
    ) -> str:
        timeout_s = max(5.0, float(self.config.board_ready_timeout_s))
        poll_s = max(0.5, float(self.config.board_ready_poll_s))
        deadline = time.time() + timeout_s
        candidate_ids = [initial_board_id]

        while time.time() < deadline:
            for resolved in self._resolve_board_ids(request_refs):
                if resolved not in candidate_ids:
                    candidate_ids.insert(0, resolved)

            for candidate_id in candidate_ids:
                if self._board_exists(candidate_id):
                    return candidate_id

            time.sleep(poll_s)

        return candidate_ids[0]

    def _board_exists(self, board_id: str) -> bool:
        endpoints = [
            "/api/v1/boards/{task_id}/details",
            self.config.status_path_template,
        ]
        if self.config.bearer_token:
            endpoints.append(self.config.alt_status_path_template)

        for endpoint in endpoints:
            try:
                path = endpoint.format(task_id=board_id)
                self._request_payload(
                    "GET",
                    path,
                    headers={"accept": "application/json"},
                )
                return True
            except Exception:
                continue
        return False

    def _request_json(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = self._request_payload(method, path, json_body=json_body)
        if not isinstance(payload, dict):
            raise RuntimeError(f"DeepPCB JSON response was not an object: {payload!r}")
        return payload

    def _request_payload(
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
        response = self._request_raw(
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

    def _request_raw(
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
            request_headers.update(self._auth_headers())
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
                raise RuntimeError(
                    f"DeepPCB API request failed ({method} {url}) with status "
                    f"{status}. Response: {detail}"
                ) from exc

    def _persist_downloaded_layout(
        self,
        content: bytes,
        content_type: str,
        out_dir: Path,
        candidate_id: str,
    ) -> Path:
        if "zip" in content_type or _is_zip_bytes(content):
            archive_path = out_dir / f"{candidate_id}.zip"
            archive_path.write_bytes(content)
            with zipfile.ZipFile(archive_path) as archive:
                for member in archive.namelist():
                    if member.endswith(".kicad_pcb") and _match_user_layout(member):
                        archive.extract(member, path=out_dir)
                        return out_dir / member
            raise RuntimeError("DeepPCB zip download did not contain a .kicad_pcb file")

        head = content[:256].lstrip()
        if head.startswith(b"{") or head.startswith(b"["):
            raise RuntimeError(
                "DeepPCB returned JSON artifact. Automatic apply requires a "
                ".kicad_pcb candidate. Provide a download URL that returns KiCad PCB."
            )

        output_path = out_dir / f"{candidate_id}.kicad_pcb"
        output_path.write_bytes(content)
        return output_path

    def _parse_board_candidates(
        self,
        payload: dict[str, Any],
        board_id: str,
    ) -> list[AutolayoutCandidate]:
        revisions: list[dict[str, Any]] = []
        for values in _all_lists(payload):
            if not values or not all(isinstance(item, dict) for item in values):
                continue
            for item in values:
                if self._extract_string(
                    item,
                    keys=("fileUrl", "file_url", "downloadUrl", "download_url"),
                ):
                    revisions.append(item)

        candidates: list[AutolayoutCandidate] = []
        for index, revision in enumerate(revisions, start=1):
            revision_id = self._extract_string(
                revision,
                keys=("revision", "revisionNumber", "runningNumberOfRevisions", "id"),
            ) or str(index)
            score = self._candidate_score(revision)
            candidates.append(
                AutolayoutCandidate(
                    candidate_id=revision_id,
                    label=f"Revision {revision_id}",
                    score=score,
                    metadata={"boardId": board_id, **revision},
                    files={
                        "deeppcb_artifact_url": self._extract_string(
                            revision,
                            keys=("fileUrl", "file_url", "downloadUrl", "download_url"),
                        )
                        or ""
                    },
                )
            )
        return candidates

    def _parse_candidates(self, payload: dict[str, Any]) -> list[AutolayoutCandidate]:
        lists = _all_lists(payload)

        candidates: list[AutolayoutCandidate] = []
        for values in lists:
            if not values or not all(isinstance(item, dict) for item in values):
                continue
            parsed_batch = []
            for item in values:
                candidate_id = self._extract_string(
                    item,
                    keys=(
                        "candidate_id",
                        "candidateId",
                        "id",
                        "layout_id",
                        "layoutId",
                        "result_id",
                        "resultId",
                    ),
                )
                if not candidate_id:
                    parsed_batch = []
                    break
                parsed_batch.append(
                    AutolayoutCandidate(
                        candidate_id=candidate_id,
                        label=self._extract_string(
                            item,
                            keys=("name", "label", "title"),
                        ),
                        score=self._extract_float(item, keys=("score", "rank")),
                        metadata=item,
                    )
                )
            if parsed_batch:
                candidates = parsed_batch
                break

        return candidates

    def _candidate_score(self, revision: dict[str, Any]) -> float | None:
        stats = revision.get("stats")
        if not isinstance(stats, dict):
            return self._extract_float(revision, keys=("score", "rank"))

        total = self._extract_float(stats, keys=("numConnections", "numNets"))
        missing = self._extract_float(stats, keys=("numConnectionsMissing",))
        if total is None or total <= 0 or missing is None:
            return self._extract_float(revision, keys=("score", "rank"))

        completed_ratio = max(0.0, min(1.0, (total - missing) / total))
        return round(completed_ratio, 6)

    def _extract_progress(self, payload: dict[str, Any]) -> float | None:
        progress = self._extract_float(
            payload,
            keys=("progress", "percent", "percentage"),
        )
        if progress is not None:
            if progress > 1:
                return max(0.0, min(progress / 100.0, 1.0))
            return max(0.0, min(progress, 1.0))

        candidate_scores = [
            candidate.score
            for candidate in self._parse_candidates(payload)
            if candidate.score is not None
        ]
        if candidate_scores:
            return max(candidate_scores)
        return None

    def _auth_headers(self) -> dict[str, str]:
        headers = {"x-deeppcb-api-key": self.config.api_key}
        bearer_token = (self.config.bearer_token or "").strip() or self.config.api_key
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
        return headers

    def _job_type(self, request: SubmitRequest) -> str:
        explicit = request.options.get("jobType")
        if isinstance(explicit, str) and explicit:
            return explicit
        objective = str(request.options.get("objective", "")).lower()
        if "placement" in objective:
            return "Placement"
        return "Routing"

    def _routing_type(self, request: SubmitRequest) -> str:
        explicit = request.options.get("routingType")
        if isinstance(explicit, str) and explicit:
            return explicit
        preserve_existing = request.constraints.get("preserve_existing_routing")
        if preserve_existing is True:
            return "CurrentProtectedWiring"
        return "EmptyBoard"

    def _webhook_url(self, request: SubmitRequest) -> str:
        option_keys = (
            "webhook_url",
            "webhookUrl",
            "webHookUrl",
        )
        for key in option_keys:
            value = request.options.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        if self.config.webhook_url and self.config.webhook_url.strip():
            return self.config.webhook_url.strip()

        # DeepPCB currently requires a non-empty webhook URL.
        return "https://example.com/deeppcb-autolayout"

    def _webhook_token(self, request: SubmitRequest) -> str | None:
        option_keys = (
            "webhook_token",
            "webhookToken",
            "webHookToken",
        )
        for key in option_keys:
            value = request.options.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        if self.config.webhook_token and self.config.webhook_token.strip():
            return self.config.webhook_token.strip()

        return request.job_id

    def _extract_string(self, payload: Any, keys: tuple[str, ...]) -> str | None:
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

    def _extract_float(self, payload: Any, keys: tuple[str, ...]) -> float | None:
        lookup = {key.lower() for key in keys}
        for value in _walk(payload):
            if not isinstance(value, tuple) or len(value) != 2:
                continue
            key, raw = value
            if key.lower() not in lookup:
                continue
            try:
                return float(raw)
            except (TypeError, ValueError):
                continue
        return None

    def _validate_api_key(self) -> None:
        if self.config.api_key:
            return
        raise RuntimeError(
            "DeepPCB API key missing. Set ATO_DEEPPCB_API_KEY "
            "before using provider 'deeppcb'."
        )

    def _inject_constraints_file_url(self, request: SubmitRequest) -> None:
        if self._job_type(request).lower() != "placement":
            return
        if self._existing_constraints_url(request):
            return

        payload = self._constraints_payload_from_request(request)
        if payload is None:
            return

        constraints_path = request.work_dir / "deeppcb_constraints.json"
        constraints_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        self._validate_constraints_file(constraints_path)
        uploaded_url = self._upload_board_file(constraints_path)
        request.options["constraintsFileUrl"] = uploaded_url

    def _existing_constraints_url(self, request: SubmitRequest) -> str | None:
        keys = ("constraintsFileUrl", "constraints_file_url")
        for key in keys:
            raw = request.options.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
        return None

    def _constraints_payload_from_request(
        self,
        request: SubmitRequest,
    ) -> dict[str, Any] | None:
        raw = request.constraints.get("decoupling_constraints")
        if not isinstance(raw, dict) or not raw:
            return None
        return {"decoupling_constraints": raw}

    def _validate_constraints_file(self, constraints_path: Path) -> None:
        with constraints_path.open("rb") as file_obj:
            files = {
                "constraintsJsonFile": (
                    constraints_path.name,
                    file_obj,
                    "application/json",
                )
            }
            payload = self._request_payload(
                "POST",
                _DEEPPCB_CHECK_CONSTRAINTS_PATH.get(),
                files=files,
                headers={"accept": "application/json"},
            )

        if isinstance(payload, dict):
            is_valid = payload.get("is_valid")
            if is_valid is None:
                is_valid = payload.get("isValid")
            if is_valid is False:
                detail = payload.get("error") or payload.get("message") or payload
                raise RuntimeError(f"DeepPCB constraints validation failed: {detail}")

    def _resume_board_id(self, request: SubmitRequest) -> str | None:
        keys = (
            "resume_board_id",
            "resumeBoardId",
            "provider_job_ref",
            "providerJobRef",
        )
        for key in keys:
            raw = request.options.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
        return None

    def _resume_stop_first(self, request: SubmitRequest) -> bool:
        raw = request.options.get("resume_stop_first")
        if raw is None:
            raw = request.options.get("resumeStopFirst")
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            normalized = raw.strip().lower()
            if normalized in {"0", "false", "no"}:
                return False
            if normalized in {"1", "true", "yes"}:
                return True
        return True

    def _wait_for_board_not_running(self, board_id: str) -> None:
        deadline = time.time() + 30.0
        while time.time() < deadline:
            payload = None
            for template in (
                self.config.status_path_template,
                self.config.alt_status_path_template,
            ):
                if (
                    template == self.config.alt_status_path_template
                    and not self.config.bearer_token
                ):
                    continue
                try:
                    payload = self._request_payload(
                        "GET",
                        template.format(task_id=board_id),
                        headers={"accept": "application/json"},
                    )
                    break
                except Exception:
                    continue

            if payload is None:
                return

            statuses = _extract_workflow_statuses(payload)
            if not statuses:
                return
            if not any(_is_running_workflow_status(status) for status in statuses):
                return
            time.sleep(1.0)


def _join_url(base_url: str, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _walk(payload: Any):
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield (key, value)
            yield from _walk(value)
    elif isinstance(payload, list):
        for value in payload:
            yield from _walk(value)


def _all_lists(payload: Any) -> list[list[Any]]:
    found: list[list[Any]] = []
    if isinstance(payload, list):
        found.append(payload)
        for item in payload:
            found.extend(_all_lists(item))
    elif isinstance(payload, dict):
        for value in payload.values():
            found.extend(_all_lists(value))
    return found


def _map_provider_state(raw: str | None) -> AutolayoutState:
    if not raw:
        return AutolayoutState.RUNNING

    normalized = raw.strip().lower()
    if normalized in {"queued", "pending", "created"}:
        return AutolayoutState.QUEUED
    if normalized in {"running", "processing", "in_progress", "in-progress"}:
        return AutolayoutState.RUNNING
    if normalized in {
        "done",
        "completed",
        "success",
        "succeeded",
        "finished",
    }:
        return AutolayoutState.COMPLETED
    if normalized in {"failed", "error", "aborted"}:
        return AutolayoutState.FAILED
    if normalized in {"cancelled", "canceled"}:
        return AutolayoutState.CANCELLED
    return AutolayoutState.RUNNING


def _dict_keys(payload: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(payload, dict):
        keys.update(payload.keys())
        for value in payload.values():
            keys.update(_dict_keys(value))
    elif isinstance(payload, list):
        for value in payload:
            keys.update(_dict_keys(value))
    return keys


def _is_zip_bytes(content: bytes) -> bool:
    return len(content) >= 4 and content[:4] == b"PK\x03\x04"


def _match_user_layout(path_str: str) -> bool:
    name = Path(path_str).name
    return not (name.startswith("_autosave-") or name.endswith("-save.kicad_pcb"))


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


def _extract_workflow_statuses(payload: Any) -> list[str]:
    statuses: list[str] = []
    if not isinstance(payload, dict):
        return statuses

    workflows = payload.get("workflows")
    if isinstance(workflows, list):
        for workflow in workflows:
            if not isinstance(workflow, dict):
                continue
            status = workflow.get("status")
            if isinstance(status, str) and status.strip():
                statuses.append(status.strip())

    top_level_status = payload.get("status") or payload.get("boardStatus")
    if isinstance(top_level_status, str) and top_level_status.strip():
        statuses.append(top_level_status.strip())

    return statuses


def _is_running_workflow_status(raw: str) -> bool:
    normalized = raw.strip().lower()
    return normalized in {
        "running",
        "started",
        "starting",
        "receivingrevisions",
        "stoprequested",
        "processing",
        "in_progress",
        "in-progress",
    }
