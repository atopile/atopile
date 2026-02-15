"""DeepPCB autolayout adapter.

This adapter is intentionally tolerant to response shape changes because the
public docs/API payload examples are evolving.
"""

from __future__ import annotations

import json
import time
import zipfile
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
from faebryk.libs.deeppcb import (
    DeepPCBApiClient,
    DeepPCBConfig,
    _extract_board_candidates,
    _guess_content_type,
    _parse_json_or_text,
    _pretty_json,
    _walk,
)
from faebryk.libs.deeppcb import (
    _redact_sensitive_values as _lib_redact_sensitive_values,
)


class DeepPCBAutolayout:
    """DeepPCB autolayout orchestration built on top of the API client."""

    name = "deeppcb"
    capabilities = ProviderCapabilities(
        supports_cancel=True,
        supports_candidates=True,
        supports_download=True,
    )

    def __init__(
        self,
        config: DeepPCBConfig | None = None,
        api: DeepPCBApiClient | None = None,
    ) -> None:
        self._api = api or DeepPCBApiClient(config=config)
        self.config = self._api.config
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
        target_layout_path: Path | None = None,
    ) -> DownloadResult:
        self._validate_api_key()
        out_dir.mkdir(parents=True, exist_ok=True)

        candidate = self._candidate_by_id(external_job_id, candidate_id)
        revision: str | None = None
        download_url = None
        if candidate is not None:
            download_url = self._extract_string(
                candidate.metadata,
                keys=("fileUrl", "file_url", "download_url", "downloadUrl", "url"),
            )
            revision = self._extract_string(
                candidate.metadata,
                keys=(
                    "revision",
                    "revisionNumber",
                    "runningNumberOfRevisions",
                    "candidate_id",
                ),
            )
            if revision is None:
                json_file_path = self._extract_string(
                    candidate.metadata,
                    keys=("jsonFilePath", "json_file_path"),
                )
                revision = _extract_revision_from_json_path(json_file_path)

        if download_url:
            response = self._request_raw(
                "GET",
                download_url,
                is_absolute_url=True,
                include_auth_headers=False,
            )
        else:
            if revision is None and candidate_id.isdigit():
                revision = candidate_id

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
            params: dict[str, str] = {"type": "KicadFile"}
            if revision:
                params["revision"] = revision

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
            direct_url = None
            if isinstance(payload, str):
                raw_url = payload.strip().strip('"')
                if raw_url.startswith(("https://", "http://")):
                    direct_url = raw_url
            elif isinstance(payload, dict):
                raw_url = self._extract_string(
                    payload,
                    keys=("url", "download_url", "downloadUrl", "fileUrl"),
                )
                if isinstance(raw_url, str) and raw_url.startswith(
                    ("https://", "http://")
                ):
                    direct_url = raw_url

            if direct_url:
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
            target_layout_path=target_layout_path,
        )

        files: dict[str, str] = {"kicad_pcb": str(output_path)}

        return DownloadResult(
            candidate_id=candidate_id,
            layout_path=output_path,
            files=files,
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
        return self._api.upload_board_file(board_path)

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
        return self._api.request_payload(
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
        return self._api.request_raw(
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

    def _persist_downloaded_layout(
        self,
        content: bytes,
        content_type: str,
        out_dir: Path,
        candidate_id: str,
        target_layout_path: Path | None = None,
    ) -> Path:
        _ = target_layout_path
        out_dir.mkdir(parents=True, exist_ok=True)

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
                "DeepPCB returned a JSON artifact for candidate download. "
                "Only KiCad artifacts are supported for apply."
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

        # Prefer explicit workflow revisions when available. These carry
        # revisionNumber/jsonFilePath even when fileUrl is omitted.
        workflows = payload.get("workflows")
        if isinstance(workflows, list):
            for workflow in workflows:
                if not isinstance(workflow, dict):
                    continue
                workflow_id = self._extract_string(
                    workflow,
                    keys=("workflowId", "workflow_id", "id"),
                )
                workflow_revisions = workflow.get("revisions")
                if not isinstance(workflow_revisions, list):
                    continue
                for item in workflow_revisions:
                    if not isinstance(item, dict):
                        continue
                    revision = dict(item)
                    if workflow_id and "workflowId" not in revision:
                        revision["workflowId"] = workflow_id
                    revisions.append(revision)

        if not revisions:
            for values in _all_lists(payload):
                if not values or not all(isinstance(item, dict) for item in values):
                    continue
                for item in values:
                    has_artifact_ref = self._extract_string(
                        item,
                        keys=(
                            "fileUrl",
                            "file_url",
                            "downloadUrl",
                            "download_url",
                            "jsonFilePath",
                            "json_file_path",
                        ),
                    )
                    has_revision_ref = self._extract_string(
                        item,
                        keys=(
                            "revision",
                            "revisionNumber",
                            "runningNumberOfRevisions",
                        ),
                    )
                    if has_artifact_ref or has_revision_ref:
                        revisions.append(item)

        ranked_candidates: list[tuple[float, int, AutolayoutCandidate]] = []
        seen_ids: set[str] = set()
        for index, revision in enumerate(revisions, start=1):
            revision_number = self._extract_string(
                revision,
                keys=("revision", "revisionNumber", "runningNumberOfRevisions"),
            )
            revision_id = self._extract_string(revision, keys=("id", "revisionId"))
            candidate_id = revision_number or revision_id or str(index)
            if candidate_id in seen_ids:
                continue
            seen_ids.add(candidate_id)

            metadata = {"boardId": board_id, **revision}
            if revision_number and "revision" not in metadata:
                metadata["revision"] = revision_number
            if revision_id and "revisionId" not in metadata:
                metadata["revisionId"] = revision_id

            files: dict[str, str] = {}
            artifact_url = self._extract_string(
                revision,
                keys=("fileUrl", "file_url", "downloadUrl", "download_url", "url"),
            )
            if artifact_url:
                files["deeppcb_artifact_url"] = artifact_url

            score = self._candidate_score(revision)
            candidate = AutolayoutCandidate(
                candidate_id=candidate_id,
                label=f"Revision {revision_number or candidate_id}",
                score=score,
                metadata=metadata,
                files=files,
            )

            revision_order = self._extract_float(
                revision,
                keys=("revision", "revisionNumber", "runningNumberOfRevisions"),
            )
            ranked_candidates.append(
                (
                    revision_order if revision_order is not None else float("-inf"),
                    index,
                    candidate,
                )
            )

        # Prefer newest revision first when explicit revision numbers are known.
        if any(order > float("-inf") for order, _, _ in ranked_candidates):
            ranked_candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)

        return [candidate for _, _, candidate in ranked_candidates]

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
            result = revision.get("result")
            if isinstance(result, dict):
                stats = result

        if not isinstance(stats, dict):
            return self._extract_float(revision, keys=("score", "rank", "fitnessScore"))

        total = self._extract_float(
            stats,
            keys=("numConnections", "numNets", "totalAirWires"),
        )
        missing = self._extract_float(
            stats,
            keys=("numConnectionsMissing", "airWiresNotConnected"),
        )
        if total is None or total <= 0 or missing is None:
            return self._extract_float(
                stats,
                keys=("score", "rank", "fitnessScore"),
            ) or self._extract_float(revision, keys=("score", "rank", "fitnessScore"))

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
        return self._api.auth_headers()

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
                self.config.check_constraints_path,
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


DeepPCBProvider = DeepPCBAutolayout


def _extract_revision_from_json_path(path: str | None) -> str | None:
    if not isinstance(path, str) or not path.strip():
        return None

    parts = [token for token in path.replace("\\", "/").split("/") if token]
    for index, token in enumerate(parts[:-1]):
        if token.lower() != "revisions":
            continue
        candidate = parts[index + 1].strip()
        if candidate:
            return candidate
    return None


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


def _is_zip_bytes(content: bytes) -> bool:
    return len(content) >= 4 and content[:4] == b"PK\x03\x04"


def _match_user_layout(path_str: str) -> bool:
    name = Path(path_str).name
    return not (name.startswith("_autosave-") or name.endswith("-save.kicad_pcb"))


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


def _redact_sensitive_values(
    text: str,
    values: tuple[str | None, ...],
) -> str:
    return _lib_redact_sensitive_values(text, values)
