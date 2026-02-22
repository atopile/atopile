"""REST routes for DeepPCB autolayout jobs."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from atopile.server.domains.autolayout.service import get_autolayout_service
from atopile.server.domains.autolayout.webhook_gateway import (
    default_internal_api_base_url,
    get_autolayout_webhook_gateway_manager,
)

router = APIRouter(prefix="/api/autolayout", tags=["autolayout"])


class StartAutolayoutRequest(BaseModel):
    """Request payload for starting a new autolayout job."""

    model_config = ConfigDict(populate_by_name=True)

    project_root: str = Field(alias="projectRoot")
    build_target: str = Field(default="default", alias="buildTarget")
    constraints: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class StartAutolayoutResponse(BaseModel):
    """Response payload for a newly started autolayout job."""

    job: dict[str, Any]


class GetAutolayoutJobResponse(BaseModel):
    """Response payload for a single autolayout job."""

    job: dict[str, Any]


class ListAutolayoutJobsResponse(BaseModel):
    """Response payload for autolayout job history."""

    jobs: list[dict[str, Any]]


class ListAutolayoutCandidatesResponse(BaseModel):
    """Response payload for autolayout candidates."""

    candidates: list[dict[str, Any]]


class DeeppcbWebhookResponse(BaseModel):
    """Response payload for DeepPCB webhook ingestion."""

    accepted: bool
    matched: bool
    job_id: str | None = None
    state: str | None = None
    provider_job_ref: str | None = None
    candidate_count: int | None = None
    reason: str | None = None


class StartWebhookGatewayRequest(BaseModel):
    """Request payload for local webhook gateway startup."""

    model_config = ConfigDict(populate_by_name=True)

    internal_api_base_url: str | None = Field(default=None, alias="internalApiBaseUrl")
    webhook_path: str = Field(
        default="/api/autolayout/webhooks/deeppcb",
        alias="webhookPath",
    )
    tunnel_provider: str = Field(default="cloudflared", alias="tunnelProvider")
    gateway_host: str = Field(default="127.0.0.1", alias="gatewayHost")
    gateway_port: int = Field(default=0, alias="gatewayPort")
    webhook_token: str | None = Field(default=None, alias="webhookToken")


class WebhookGatewayResponse(BaseModel):
    """Response payload for webhook gateway status."""

    status: dict[str, Any]


@router.post("/jobs", response_model=StartAutolayoutResponse)
async def start_autolayout_job(
    request: StartAutolayoutRequest,
) -> StartAutolayoutResponse:
    """Start an autolayout job for a project/build target."""
    project_path = Path(request.project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Project not found: {request.project_root}",
        )

    service = get_autolayout_service()
    job = await asyncio.to_thread(
        service.start_job,
        request.project_root,
        request.build_target,
        request.constraints,
        request.options,
    )
    return StartAutolayoutResponse(job=job.to_dict())


@router.get("/jobs", response_model=ListAutolayoutJobsResponse)
async def list_autolayout_jobs(
    project_root: str | None = Query(None, alias="project_root"),
) -> ListAutolayoutJobsResponse:
    """List autolayout jobs, optionally filtered by project root."""
    if project_root:
        project_path = Path(project_root)
        if not project_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Project not found: {project_root}",
            )

    service = get_autolayout_service()
    jobs = await asyncio.to_thread(service.list_jobs, project_root)
    return ListAutolayoutJobsResponse(jobs=[job.to_dict() for job in jobs])


@router.get("/jobs/{job_id}", response_model=GetAutolayoutJobResponse)
async def get_autolayout_job(
    job_id: str,
    refresh: bool = Query(False),
) -> GetAutolayoutJobResponse:
    """Get current state for an autolayout job."""
    service = get_autolayout_service()
    try:
        job = await asyncio.to_thread(
            service.refresh_job if refresh else service.get_job,
            job_id,
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown autolayout job: {job_id}",
        ) from None

    return GetAutolayoutJobResponse(job=job.to_dict())


@router.get(
    "/jobs/{job_id}/candidates",
    response_model=ListAutolayoutCandidatesResponse,
)
async def list_autolayout_candidates(
    job_id: str,
    refresh: bool = Query(False),
) -> ListAutolayoutCandidatesResponse:
    """List candidates for a specific autolayout job."""
    service = get_autolayout_service()
    try:
        candidates = await asyncio.to_thread(service.list_candidates, job_id, refresh)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown autolayout job: {job_id}",
        ) from None

    return ListAutolayoutCandidatesResponse(
        candidates=[candidate.to_dict() for candidate in candidates]
    )


def _extract_deeppcb_webhook_token(
    *,
    request: Request,
    payload: dict[str, Any],
) -> str | None:
    header_candidates = [
        request.headers.get("x-webhook-token"),
        request.headers.get("x-deeppcb-webhook-token"),
        request.headers.get("x-signature"),
    ]
    auth_header = request.headers.get("authorization")
    if isinstance(auth_header, str) and auth_header.lower().startswith("bearer "):
        header_candidates.append(auth_header[7:].strip())

    for token in header_candidates:
        if isinstance(token, str) and token.strip():
            return token.strip()

    for key in ("webhookToken", "webhook_token", "token", "signature"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


@router.post("/webhooks/deeppcb", response_model=DeeppcbWebhookResponse)
async def deeppcb_webhook(
    request: Request,
) -> DeeppcbWebhookResponse:
    """Receive and apply DeepPCB webhook updates."""
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON webhook payload: {exc}",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail="DeepPCB webhook payload must be a JSON object.",
        )

    token = _extract_deeppcb_webhook_token(request=request, payload=payload)
    service = get_autolayout_service()
    try:
        result = await asyncio.to_thread(
            service.handle_deeppcb_webhook,
            payload,
            provided_token=token,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return DeeppcbWebhookResponse(**result)


@router.post("/dev/webhook-gateway/start", response_model=WebhookGatewayResponse)
async def start_webhook_gateway(
    request: StartWebhookGatewayRequest,
) -> WebhookGatewayResponse:
    """Start a webhook-only dev gateway and optional cloudflared tunnel."""
    manager = get_autolayout_webhook_gateway_manager()
    internal_base_url = (
        request.internal_api_base_url or default_internal_api_base_url()
    )
    try:
        status = await asyncio.to_thread(
            manager.start,
            internal_base_url=internal_base_url,
            webhook_path=request.webhook_path,
            gateway_host=request.gateway_host,
            gateway_port=request.gateway_port,
            tunnel_provider=request.tunnel_provider,
            webhook_token=request.webhook_token,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    service = get_autolayout_service()
    webhook_url = status.get("webhook_url")
    if isinstance(webhook_url, str) and webhook_url.strip():
        await asyncio.to_thread(
            service.configure_deeppcb_webhook_defaults,
            webhook_url=webhook_url,
            webhook_token=status.get("webhook_token"),
        )
    return WebhookGatewayResponse(status=status)


@router.get("/dev/webhook-gateway/status", response_model=WebhookGatewayResponse)
async def get_webhook_gateway_status() -> WebhookGatewayResponse:
    """Get current dev webhook gateway state."""
    manager = get_autolayout_webhook_gateway_manager()
    status = await asyncio.to_thread(manager.status)
    return WebhookGatewayResponse(status=status)


@router.post("/dev/webhook-gateway/stop", response_model=WebhookGatewayResponse)
async def stop_webhook_gateway() -> WebhookGatewayResponse:
    """Stop dev webhook gateway/tunnel."""
    manager = get_autolayout_webhook_gateway_manager()
    status = await asyncio.to_thread(manager.stop)
    return WebhookGatewayResponse(status=status)
