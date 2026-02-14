"""Autolayout CLI commands."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import typer

from atopile.server.domains.autolayout.models import (
    TERMINAL_AUTO_LAYOUT_STATES,
    AutolayoutCandidate,
    AutolayoutJob,
    AutolayoutState,
)
from atopile.server.domains.autolayout.service import get_autolayout_service
from atopile.telemetry import capture

autolayout_app = typer.Typer(rich_markup_mode="rich")


def _print_json(payload: dict) -> None:
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


def _build_provider_options(
    webhook_url: str | None,
    webhook_token: str | None,
    timeout_minutes: int | None,
    max_batch_timeout: int | None,
    response_board_format: int | None,
    *,
    job_type: str | None = None,
) -> dict[str, object]:
    options: dict[str, object] = {}
    if webhook_url:
        options["webhook_url"] = webhook_url
    if webhook_token:
        options["webhook_token"] = webhook_token
    if timeout_minutes is not None:
        options["timeout"] = timeout_minutes
    if max_batch_timeout is not None:
        options["maxBatchTimeout"] = max_batch_timeout
    if response_board_format is not None:
        options["responseBoardFormat"] = response_board_format
    if job_type:
        options["jobType"] = job_type
    return options


def _merge_provider_options(
    base: dict[str, object],
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    merged = dict(base)
    if extra:
        merged.update(extra)
    return merged


def _wait_for_candidates(
    service: Any,
    job_id: str,
    poll_seconds: float,
    max_wait_seconds: float,
) -> tuple[AutolayoutJob, list[AutolayoutCandidate]]:
    deadline = None
    if max_wait_seconds > 0:
        deadline = time.time() + max_wait_seconds

    while True:
        candidates = service.list_candidates(job_id, refresh=True)
        job = service.get_job(job_id)
        if candidates:
            return job, candidates
        if job.state in TERMINAL_AUTO_LAYOUT_STATES:
            return job, candidates
        if deadline is not None and time.time() >= deadline:
            return job, candidates
        time.sleep(poll_seconds)


def _choose_candidate(
    candidates: list[AutolayoutCandidate],
    candidate_id: str | None = None,
) -> AutolayoutCandidate:
    if not candidates:
        raise ValueError("No candidates are available for review")

    if candidate_id:
        for candidate in candidates:
            if candidate.candidate_id == candidate_id:
                return candidate
        raise ValueError(f"Candidate '{candidate_id}' not found")

    scored_candidates = [
        candidate for candidate in candidates if candidate.score is not None
    ]
    if scored_candidates:
        return max(
            scored_candidates,
            key=lambda candidate: float(candidate.score or 0.0),
        )
    return candidates[0]


def _placement_ai_review(
    candidate: AutolayoutCandidate,
    min_score: float,
) -> tuple[bool, str, dict[str, int]]:
    severity_counts = {"ERROR": 0, "WARNING": 0, "INFO": 0}
    anomaly_keys = ("placementAnomalies", "routingAnomalies", "anomalies")
    for key in anomaly_keys:
        anomalies = candidate.metadata.get(key)
        if not isinstance(anomalies, list):
            continue
        for anomaly in anomalies:
            if not isinstance(anomaly, dict):
                continue
            severity = str(anomaly.get("severity", "")).upper().strip()
            if severity in severity_counts:
                severity_counts[severity] += 1

    if severity_counts["ERROR"] > 0:
        return (
            False,
            "Rejected by AI review: placement contains ERROR anomalies",
            severity_counts,
        )

    score = candidate.score
    if score is not None and score < min_score:
        return (
            False,
            (
                "Rejected by AI review: score "
                f"{score:.4f} is below threshold {min_score:.4f}"
            ),
            severity_counts,
        )

    return (True, "Approved by AI review", severity_counts)


def _manual_review_decision(
    candidate: AutolayoutCandidate,
    auto_approve: bool,
) -> tuple[bool, str]:
    if auto_approve:
        return True, "Approved by --approve-placement flag"

    if not sys.stdin.isatty():
        return (
            False,
            "Manual review requires an interactive terminal or --approve-placement",
        )

    approved = typer.confirm(
        (
            "Approve placement candidate "
            f"'{candidate.candidate_id}'"
            + (f" (score={candidate.score:.4f})" if candidate.score is not None else "")
            + " for routing?"
        ),
        default=False,
    )
    if approved:
        return True, "Approved manually"
    return False, "Rejected manually"


@autolayout_app.command("run")
@capture("cli:autolayout_run_start", "cli:autolayout_run_end")
def run_autolayout(
    build: str = typer.Option("default", "--build", "-b", help="Build target name"),
    project_root: Path = typer.Option(Path.cwd(), "--project-root", "-p"),
    provider: str | None = typer.Option(None, "--provider", help="Provider id"),
    webhook_url: str | None = typer.Option(
        None,
        "--webhook-url",
        help="Webhook URL for DeepPCB board events",
    ),
    webhook_token: str | None = typer.Option(
        None,
        "--webhook-token",
        help="Webhook token for DeepPCB callbacks",
    ),
    timeout_minutes: int | None = typer.Option(
        None,
        "--timeout-minutes",
        min=1,
        help="DeepPCB confirm timeout in minutes",
    ),
    max_batch_timeout: int | None = typer.Option(
        None,
        "--max-batch-timeout",
        min=1,
        help="DeepPCB batch timeout in seconds",
    ),
    response_board_format: int | None = typer.Option(
        None,
        "--response-board-format",
        min=1,
        max=4,
        help="DeepPCB response board format (1=JSON,2=JSON-wiring,3=DSN,4=SES)",
    ),
    job_type: str | None = typer.Option(
        None,
        "--job-type",
        help="DeepPCB job type override (Placement or Routing)",
    ),
    resume_board_id: str | None = typer.Option(
        None,
        "--resume-board-id",
        help="DeepPCB board ID to resume instead of creating a new board",
    ),
    resume_stop_first: bool = typer.Option(
        True,
        "--resume-stop-first/--no-resume-stop-first",
        help="Stop existing run before resume",
    ),
    wait: bool = typer.Option(
        False,
        "--wait",
        help="Poll provider until job reaches a terminal state",
    ),
    poll_seconds: float = typer.Option(2.0, "--poll-seconds", min=0.5),
) -> None:
    """Submit a new autolayout job."""
    service = get_autolayout_service()
    options = _build_provider_options(
        webhook_url=webhook_url,
        webhook_token=webhook_token,
        timeout_minutes=timeout_minutes,
        max_batch_timeout=max_batch_timeout,
        response_board_format=response_board_format,
        job_type=job_type,
    )
    if resume_board_id:
        options["resume_board_id"] = resume_board_id
        options["resume_stop_first"] = resume_stop_first

    job = service.start_job(
        project_root=str(project_root),
        build_target=build,
        provider_name=provider,
        options=options or None,
    )

    if not wait:
        _print_json({"success": True, "job": job.to_dict()})
        return

    while job.state not in TERMINAL_AUTO_LAYOUT_STATES:
        time.sleep(poll_seconds)
        job = service.refresh_job(job.job_id)

    _print_json({"success": True, "job": job.to_dict()})


@autolayout_app.command("run-flow")
@capture("cli:autolayout_run_flow_start", "cli:autolayout_run_flow_end")
def run_autolayout_flow(
    build: str = typer.Option("default", "--build", "-b", help="Build target name"),
    project_root: Path = typer.Option(Path.cwd(), "--project-root", "-p"),
    provider: str | None = typer.Option(None, "--provider", help="Provider id"),
    webhook_url: str | None = typer.Option(
        None,
        "--webhook-url",
        help="Webhook URL for DeepPCB board events",
    ),
    webhook_token: str | None = typer.Option(
        None,
        "--webhook-token",
        help="Webhook token for DeepPCB callbacks",
    ),
    placement_timeout_minutes: int = typer.Option(
        10,
        "--placement-timeout-minutes",
        min=1,
        help="DeepPCB placement timeout in minutes",
    ),
    routing_timeout_minutes: int = typer.Option(
        10,
        "--routing-timeout-minutes",
        min=1,
        help="DeepPCB routing timeout in minutes",
    ),
    max_batch_timeout: int | None = typer.Option(
        None,
        "--max-batch-timeout",
        min=1,
        help="DeepPCB batch timeout in seconds",
    ),
    response_board_format: int | None = typer.Option(
        None,
        "--response-board-format",
        min=1,
        max=4,
        help="DeepPCB response board format (1=JSON,2=JSON-wiring,3=DSN,4=SES)",
    ),
    review_mode: str = typer.Option(
        "manual",
        "--review-mode",
        help="Placement review mode: manual, ai, or none",
    ),
    approve_placement: bool = typer.Option(
        False,
        "--approve-placement",
        help="Auto-approve the chosen placement candidate",
    ),
    placement_candidate: str | None = typer.Option(
        None,
        "--placement-candidate",
        help="Placement candidate ID to review/apply. Defaults to best score.",
    ),
    ai_min_score: float = typer.Option(
        0.0,
        "--ai-min-score",
        help="Minimum placement score required by AI review",
    ),
    wait_max_seconds: float = typer.Option(
        240.0,
        "--wait-max-seconds",
        min=5.0,
        help="Max seconds to wait for placement candidates before review",
    ),
    poll_seconds: float = typer.Option(2.0, "--poll-seconds", min=0.5),
    wait_routing: bool = typer.Option(
        False,
        "--wait-routing",
        help="Poll routing run until terminal state",
    ),
) -> None:
    """Run Placement -> Review -> Apply -> Routing as a managed flow."""
    mode = review_mode.strip().lower()
    valid_modes = {"manual", "ai", "none"}
    if mode not in valid_modes:
        valid_modes_msg = ", ".join(sorted(valid_modes))
        raise typer.BadParameter(
            f"Invalid review mode '{review_mode}'. Use one of: {valid_modes_msg}"
        )

    service = get_autolayout_service()

    base_provider_options = _build_provider_options(
        webhook_url=webhook_url,
        webhook_token=webhook_token,
        timeout_minutes=None,
        max_batch_timeout=max_batch_timeout,
        response_board_format=response_board_format,
    )
    placement_options = _merge_provider_options(
        base_provider_options,
        {
            "jobType": "Placement",
            "timeout": placement_timeout_minutes,
        },
    )

    placement_job = service.start_job(
        project_root=str(project_root),
        build_target=build,
        provider_name=provider,
        options=placement_options,
    )

    placement_job, candidates = _wait_for_candidates(
        service=service,
        job_id=placement_job.job_id,
        poll_seconds=poll_seconds,
        max_wait_seconds=wait_max_seconds,
    )

    if placement_job.state in {AutolayoutState.FAILED, AutolayoutState.CANCELLED}:
        _print_json(
            {
                "success": False,
                "stage": "placement",
                "message": "Placement run failed before review",
                "placement_job": placement_job.to_dict(),
            }
        )
        raise typer.Exit(code=2)

    if not candidates:
        _print_json(
            {
                "success": False,
                "stage": "placement",
                "message": "No placement candidates available for review",
                "placement_job": placement_job.to_dict(),
            }
        )
        raise typer.Exit(code=2)

    selected_candidate = _choose_candidate(candidates, placement_candidate)

    review_payload: dict[str, Any] = {"mode": mode, "approved": True, "reason": ""}
    if mode == "manual":
        approved, reason = _manual_review_decision(
            selected_candidate,
            auto_approve=approve_placement,
        )
        review_payload["approved"] = approved
        review_payload["reason"] = reason
    elif mode == "ai":
        approved, reason, severity_counts = _placement_ai_review(
            selected_candidate,
            min_score=ai_min_score,
        )
        review_payload["approved"] = approved
        review_payload["reason"] = reason
        review_payload["severity_counts"] = severity_counts
    else:
        review_payload["reason"] = "Review skipped (mode=none)"

    review_payload["selected_candidate_id"] = selected_candidate.candidate_id
    review_payload["selected_candidate_score"] = selected_candidate.score

    placement_applied_job: dict[str, Any] | None = None
    if not review_payload["approved"]:
        _print_json(
            {
                "success": False,
                "stage": "placement_review",
                "review": review_payload,
                "placement_job": placement_job.to_dict(),
                "candidates": [candidate.to_dict() for candidate in candidates],
            }
        )
        raise typer.Exit(code=3)

    routing_options = _merge_provider_options(
        base_provider_options,
        {
            "jobType": "Routing",
            "timeout": routing_timeout_minutes,
        },
    )

    if placement_job.provider == "deeppcb" and placement_job.provider_job_ref:
        service.select_candidate(placement_job.job_id, selected_candidate.candidate_id)
        routing_options = _merge_provider_options(
            routing_options,
            {
                "resume_board_id": placement_job.provider_job_ref,
                "resume_stop_first": True,
            },
        )
        placement_applied_job = {
            "mode": "remote_resume",
            "message": (
                "DeepPCB flow uses provider-side resume for routing after review. "
                "No local placement artifact apply was needed."
            ),
            "provider_job_ref": placement_job.provider_job_ref,
            "selected_candidate_id": selected_candidate.candidate_id,
        }
    else:
        service.select_candidate(placement_job.job_id, selected_candidate.candidate_id)
        applied = service.apply_candidate(
            placement_job.job_id,
            candidate_id=selected_candidate.candidate_id,
        )
        placement_applied_job = applied.to_dict()

    routing_job = service.start_job(
        project_root=str(project_root),
        build_target=build,
        provider_name=provider,
        options=routing_options,
    )

    if wait_routing:
        while routing_job.state not in TERMINAL_AUTO_LAYOUT_STATES:
            time.sleep(poll_seconds)
            routing_job = service.refresh_job(routing_job.job_id)

    _print_json(
        {
            "success": True,
            "flow": {
                "placement_job": placement_job.to_dict(),
                "placement_review": review_payload,
                "placement_apply": placement_applied_job,
                "routing_job": routing_job.to_dict(),
            },
        }
    )


@autolayout_app.command("status")
@capture("cli:autolayout_status_start", "cli:autolayout_status_end")
def autolayout_status(
    job_id: str,
    refresh: bool = typer.Option(True, "--refresh/--no-refresh"),
) -> None:
    """Get autolayout job status."""
    service = get_autolayout_service()
    job = service.refresh_job(job_id) if refresh else service.get_job(job_id)
    _print_json({"success": True, "job": job.to_dict()})


@autolayout_app.command("jobs")
@capture("cli:autolayout_jobs_start", "cli:autolayout_jobs_end")
def autolayout_jobs(
    project_root: str | None = typer.Option(None, "--project-root", "-p"),
) -> None:
    """List autolayout jobs in memory."""
    service = get_autolayout_service()
    jobs = [job.to_dict() for job in service.list_jobs(project_root)]
    _print_json({"success": True, "jobs": jobs})


@autolayout_app.command("candidates")
@capture("cli:autolayout_candidates_start", "cli:autolayout_candidates_end")
def autolayout_candidates(
    job_id: str,
    refresh: bool = typer.Option(True, "--refresh/--no-refresh"),
) -> None:
    """List candidates for an autolayout job."""
    service = get_autolayout_service()
    candidates = [
        candidate.to_dict() for candidate in service.list_candidates(job_id, refresh)
    ]
    _print_json({"success": True, "candidates": candidates})


@autolayout_app.command("apply")
@capture("cli:autolayout_apply_start", "cli:autolayout_apply_end")
def autolayout_apply(
    job_id: str,
    candidate_id: str | None = typer.Option(None, "--candidate", "-c"),
    manual_layout_path: Path | None = typer.Option(
        None,
        "--manual-layout-path",
        help="Use a local .kicad_pcb file instead of provider download",
    ),
) -> None:
    """Apply a candidate to the target layout file."""
    service = get_autolayout_service()
    job = service.apply_candidate(
        job_id,
        candidate_id=candidate_id,
        manual_layout_path=str(manual_layout_path) if manual_layout_path else None,
    )
    _print_json({"success": True, "job": job.to_dict()})


@autolayout_app.command("cancel")
@capture("cli:autolayout_cancel_start", "cli:autolayout_cancel_end")
def autolayout_cancel(job_id: str) -> None:
    """Cancel an autolayout job."""
    service = get_autolayout_service()
    job = service.cancel_job(job_id)
    _print_json({"success": True, "job": job.to_dict()})


@autolayout_app.command("export-quilter")
@capture("cli:autolayout_export_quilter_start", "cli:autolayout_export_quilter_end")
def export_quilter(
    build: str = typer.Option("default", "--build", "-b", help="Build target name"),
    project_root: Path = typer.Option(Path.cwd(), "--project-root", "-p"),
) -> None:
    """Create a manual-upload package for Quilter."""
    service = get_autolayout_service()
    package_path = service.export_quilter_package(str(project_root), build)
    _print_json({"success": True, "packagePath": package_path})
