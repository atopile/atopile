"""Autolayout service orchestration for DeepPCB-backed AI layout."""

from __future__ import annotations

import copy
import json
import logging
import shutil
import threading
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from atopile.config import ProjectConfig
from atopile.server.domains.autolayout.models import (
    AutolayoutCandidate,
    AutolayoutJob,
    AutolayoutState,
    ResolvedAutolayoutTargetFiles,
    SubmitRequest,
    utc_now_iso,
)
from atopile.server.events import event_bus
from faebryk.exporters.pcb.deeppcb.transformer import DeepPCB_Transformer
from faebryk.exporters.pcb.autolayout.deeppcb import DeepPCBAutolayout
from faebryk.libs.kicad.fileformats import kicad
from faebryk.libs.paths import get_log_dir

log = logging.getLogger(__name__)


class AutolayoutServiceSettings(BaseSettings):
    """Feature-level settings for autolayout service behavior."""

    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
        case_sensitive=False,
    )

    enable_autolayout: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "ATO_ENABLE_AUTOLAYOUT",
            "ENABLE_AUTOLAYOUT",
            "FBRK_ENABLE_AUTOLAYOUT",
        ),
    )


class AutolayoutService:
    """Coordinates DeepPCB submission, polling, candidate selection, and apply."""

    def __init__(
        self,
        state_path: str | Path | None = None,
        max_persisted_jobs: int = 200,
        settings: AutolayoutServiceSettings | None = None,
    ) -> None:
        self._autolayout = DeepPCBAutolayout()
        self._settings = settings or AutolayoutServiceSettings()
        self._jobs: dict[str, AutolayoutJob] = {}
        self._lock = threading.RLock()
        self._state_path = (
            Path(state_path).expanduser()
            if state_path is not None
            else get_log_dir() / "autolayout_jobs_state.json"
        )
        self._max_persisted_jobs = max(20, min(int(max_persisted_jobs), 20_000))
        self._state_version = 1
        self._state_mtime_ns = 0
        self._load_jobs_from_disk()

    def start_job(
        self,
        project_root: str,
        build_target: str,
        constraints: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> AutolayoutJob:
        self._ensure_enabled()
        with self._lock:
            self._maybe_reload_jobs_from_disk_locked()

        target_files = self._resolve_target_files(project_root, build_target)
        provider = self._autolayout

        job_id = f"al-{uuid.uuid4().hex[:12]}"
        work_dir = target_files.work_root / job_id
        work_dir.mkdir(parents=True, exist_ok=True)

        merged_constraints = dict(target_files.default_constraints)
        if constraints:
            merged_constraints.update(constraints)

        merged_options = dict(target_files.default_options)
        if options:
            merged_options.update(options)

        zip_path = self._prepare_input_package(
            work_dir=work_dir,
            layout_path=target_files.layout_path,
            kicad_project_path=target_files.kicad_project_path,
            schematic_path=target_files.schematic_path,
            constraints=merged_constraints,
        )
        provider_input_path = self._prepare_provider_input(
            work_dir=work_dir,
            layout_path=target_files.layout_path,
            deeppcb_path=target_files.deeppcb_path,
        )

        job = AutolayoutJob(
            job_id=job_id,
            project_root=str(target_files.project_root),
            build_target=build_target,
            provider=provider.name,
            state=AutolayoutState.QUEUED,
            created_at=utc_now_iso(),
            updated_at=utc_now_iso(),
            constraints=merged_constraints,
            options=merged_options,
            input_zip_path=str(zip_path),
            work_dir=str(work_dir),
            layout_path=str(target_files.layout_path),
        )

        with self._lock:
            self._jobs[job_id] = job
            self._trim_jobs_locked()
            self._persist_jobs_locked()

        try:
            submit_result = provider.submit(
                SubmitRequest(
                    job_id=job_id,
                    project_root=Path(job.project_root),
                    build_target=build_target,
                    layout_path=Path(job.layout_path),
                    provider_input_path=provider_input_path,
                    input_zip_path=zip_path,
                    work_dir=work_dir,
                    constraints=merged_constraints,
                    options=merged_options,
                    kicad_project_path=target_files.kicad_project_path,
                    schematic_path=target_files.schematic_path,
                )
            )
        except Exception as exc:
            with self._lock:
                current = self._jobs[job_id]
                current.state = AutolayoutState.FAILED
                current.error = str(exc)
                current.message = str(exc)
                current.mark_updated()
                self._persist_jobs_locked()
                self._emit_job_event(current)
                return copy.deepcopy(current)

        with self._lock:
            current = self._jobs[job_id]
            current.provider_job_ref = submit_result.external_job_id
            current.state = submit_result.state
            current.message = submit_result.message
            current.candidates = _dedupe_candidates(submit_result.candidates)
            if current.candidates and current.state == AutolayoutState.COMPLETED:
                current.state = AutolayoutState.AWAITING_SELECTION
            current.mark_updated()
            self._persist_jobs_locked()
            self._emit_job_event(current)
            return copy.deepcopy(current)

    def get_job(self, job_id: str) -> AutolayoutJob:
        with self._lock:
            self._maybe_reload_jobs_from_disk_locked()
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(f"Unknown autolayout job: {job_id}")
            return copy.deepcopy(job)

    def list_jobs(self, project_root: str | None = None) -> list[AutolayoutJob]:
        with self._lock:
            self._maybe_reload_jobs_from_disk_locked()
            values = list(self._jobs.values())

        if project_root is not None:
            values = [job for job in values if job.project_root == project_root]

        values.sort(key=lambda job: job.created_at, reverse=True)
        return [copy.deepcopy(job) for job in values]

    def refresh_job(self, job_id: str) -> AutolayoutJob:
        with self._lock:
            self._maybe_reload_jobs_from_disk_locked()
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(f"Unknown autolayout job: {job_id}")
            if job.state in {AutolayoutState.FAILED, AutolayoutState.CANCELLED}:
                return copy.deepcopy(job)
            autolayout = self._autolayout
            provider_job_ref = job.provider_job_ref

        if not provider_job_ref:
            with self._lock:
                current = self._jobs.get(job_id)
                if current is None:
                    raise KeyError(f"Unknown autolayout job: {job_id}")
                current.state = AutolayoutState.FAILED
                current.error = "Missing DeepPCB job reference"
                current.message = "Missing DeepPCB job reference"
                current.mark_updated()
                self._persist_jobs_locked()
                self._emit_job_event(current)
                return copy.deepcopy(current)

        try:
            status = autolayout.status(provider_job_ref)
        except Exception as exc:
            with self._lock:
                current = self._jobs[job_id]
                current.state = AutolayoutState.FAILED
                current.error = str(exc)
                current.message = str(exc)
                current.mark_updated()
                self._persist_jobs_locked()
                self._emit_job_event(current)
                return copy.deepcopy(current)

        with self._lock:
            current = self._jobs[job_id]
            current.state = status.state
            current.message = status.message
            current.progress = status.progress
            if status.candidates:
                current.candidates = _dedupe_candidates(status.candidates)
                if current.state == AutolayoutState.COMPLETED:
                    current.state = AutolayoutState.AWAITING_SELECTION
            current.mark_updated()
            self._persist_jobs_locked()
            self._emit_job_event(current)
            return copy.deepcopy(current)

    def list_candidates(
        self,
        job_id: str,
        refresh: bool = True,
    ) -> list[AutolayoutCandidate]:
        job = self.refresh_job(job_id) if refresh else self.get_job(job_id)

        if job.candidates:
            return [copy.deepcopy(candidate) for candidate in job.candidates]

        if not job.provider_job_ref:
            return []

        candidates = self._autolayout.list_candidates(job.provider_job_ref)

        with self._lock:
            self._maybe_reload_jobs_from_disk_locked()
            current = self._jobs[job_id]
            current.candidates = _dedupe_candidates(candidates)
            if current.candidates and current.state == AutolayoutState.COMPLETED:
                current.state = AutolayoutState.AWAITING_SELECTION
            current.mark_updated()
            self._persist_jobs_locked()
            self._emit_job_event(current)
            return [copy.deepcopy(candidate) for candidate in current.candidates]

    def select_candidate(self, job_id: str, candidate_id: str) -> AutolayoutJob:
        with self._lock:
            self._maybe_reload_jobs_from_disk_locked()
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(f"Unknown autolayout job: {job_id}")

            if not any(c.candidate_id == candidate_id for c in job.candidates):
                raise KeyError(
                    f"Unknown candidate '{candidate_id}' for autolayout job '{job_id}'"
                )

            job.selected_candidate_id = candidate_id
            job.mark_updated()
            self._persist_jobs_locked()
            self._emit_job_event(job)
            return copy.deepcopy(job)

    def apply_candidate(
        self,
        job_id: str,
        candidate_id: str | None = None,
    ) -> AutolayoutJob:
        with self._lock:
            self._maybe_reload_jobs_from_disk_locked()
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(f"Unknown autolayout job: {job_id}")

            selected_candidate_id = candidate_id or job.selected_candidate_id
            if selected_candidate_id is None:
                raise ValueError("No candidate selected")
            provider_job_ref = job.provider_job_ref
            layout_path = Path(job.layout_path or "")

        assert selected_candidate_id is not None
        if not provider_job_ref:
            raise RuntimeError(
                "Missing DeepPCB job reference; cannot download candidate artifact."
            )
        download_result = self._autolayout.download_candidate(
            provider_job_ref,
            selected_candidate_id,
            out_dir=Path(job.work_dir or ".") / "downloads",
            target_layout_path=layout_path,
        )
        downloaded_layout = download_result.layout_path
        chosen_candidate = selected_candidate_id

        backup_path = self._apply_layout(layout_path, downloaded_layout, job_id)

        with self._lock:
            current = self._jobs[job_id]
            current.selected_candidate_id = chosen_candidate
            current.applied_candidate_id = chosen_candidate
            current.applied_layout_path = str(layout_path)
            current.backup_layout_path = str(backup_path) if backup_path else None
            current.state = AutolayoutState.COMPLETED
            current.message = "Candidate applied"
            current.error = None
            current.mark_updated()
            self._persist_jobs_locked()
            self._emit_job_event(current)
            return copy.deepcopy(current)

    def cancel_job(self, job_id: str) -> AutolayoutJob:
        with self._lock:
            self._maybe_reload_jobs_from_disk_locked()
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(f"Unknown autolayout job: {job_id}")
            provider_job_ref = job.provider_job_ref

        if provider_job_ref:
            self._autolayout.cancel(provider_job_ref)

        with self._lock:
            current = self._jobs[job_id]
            current.state = AutolayoutState.CANCELLED
            current.mark_updated()
            self._persist_jobs_locked()
            self._emit_job_event(current)
            return copy.deepcopy(current)

    def _load_jobs_from_disk(self) -> None:
        with self._lock:
            if not self._state_path.exists():
                return
            try:
                raw_payload = json.loads(self._state_path.read_text(encoding="utf-8"))
            except Exception:
                log.exception(
                    "AutolayoutService: failed to parse persisted job state at %s",
                    self._state_path,
                )
                return

            raw_jobs = raw_payload.get("jobs", []) if isinstance(raw_payload, dict) else []
            if not isinstance(raw_jobs, list):
                return

            restored: dict[str, AutolayoutJob] = {}
            for raw_job in raw_jobs:
                if not isinstance(raw_job, dict):
                    continue
                try:
                    job = AutolayoutJob.model_validate(raw_job)
                except Exception:
                    continue
                restored[job.job_id] = job

            if restored:
                self._jobs = restored
                self._trim_jobs_locked()
            self._update_state_mtime_locked()

    def _update_state_mtime_locked(self) -> None:
        try:
            self._state_mtime_ns = self._state_path.stat().st_mtime_ns
        except FileNotFoundError:
            self._state_mtime_ns = 0
        except Exception:
            self._state_mtime_ns = int(time.time_ns())

    def _maybe_reload_jobs_from_disk_locked(self) -> None:
        try:
            mtime_ns = self._state_path.stat().st_mtime_ns
        except FileNotFoundError:
            mtime_ns = 0
        except Exception:
            return
        if mtime_ns <= self._state_mtime_ns:
            return
        try:
            raw_payload = json.loads(self._state_path.read_text(encoding="utf-8"))
        except Exception:
            return
        raw_jobs = raw_payload.get("jobs", []) if isinstance(raw_payload, dict) else []
        if not isinstance(raw_jobs, list):
            return
        reloaded: dict[str, AutolayoutJob] = {}
        for raw_job in raw_jobs:
            if not isinstance(raw_job, dict):
                continue
            try:
                job = AutolayoutJob.model_validate(raw_job)
            except Exception:
                continue
            reloaded[job.job_id] = job
        if reloaded:
            self._jobs = reloaded
            self._trim_jobs_locked()
        self._state_mtime_ns = mtime_ns

    def _trim_jobs_locked(self) -> None:
        if len(self._jobs) <= self._max_persisted_jobs:
            return
        ordered = sorted(
            self._jobs.values(),
            key=lambda job: (job.created_at, job.updated_at, job.job_id),
            reverse=True,
        )
        keep_ids = {job.job_id for job in ordered[: self._max_persisted_jobs]}
        self._jobs = {job_id: job for job_id, job in self._jobs.items() if job_id in keep_ids}

    def _persist_jobs_locked(self) -> None:
        self._trim_jobs_locked()
        payload = {
            "version": self._state_version,
            "saved_at": time.time(),
            "jobs": [job.model_dump(mode="json") for job in self._jobs.values()],
        }
        tmp_path = self._state_path.with_suffix(f"{self._state_path.suffix}.tmp")
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            with tmp_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            tmp_path.replace(self._state_path)
            self._update_state_mtime_locked()
        except Exception:
            log.exception(
                "AutolayoutService: failed to persist job state to %s",
                self._state_path,
            )
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass

    def _resolve_target_files(
        self,
        project_root: str,
        build_target: str,
    ) -> ResolvedAutolayoutTargetFiles:
        project_path = Path(project_root).resolve()
        project_cfg = ProjectConfig.from_path(project_path)
        if project_cfg is None:
            raise FileNotFoundError(f"No ato.yaml found in {project_path}")

        if build_target not in project_cfg.builds:
            known = ", ".join(sorted(project_cfg.builds.keys()))
            raise KeyError(f"Unknown build target '{build_target}'. Available: {known}")

        build_cfg = project_cfg.builds[build_target]
        layout_path = build_cfg.paths.layout
        if not layout_path.exists():
            raise FileNotFoundError(
                f"Layout file not found for target '{build_target}': {layout_path}"
            )

        deeppcb_path = build_cfg.paths.output_base.with_suffix(".deeppcb")
        if not deeppcb_path.exists():
            deeppcb_path = None

        kicad_project_path = build_cfg.paths.kicad_project
        if not kicad_project_path.exists():
            kicad_project_path = None

        schematic_path = layout_path.with_suffix(".kicad_sch")
        if not schematic_path.exists():
            fallback = build_cfg.paths.output_base.with_suffix(".kicad_sch")
            schematic_path = fallback if fallback.exists() else None

        autolayout_cfg = build_cfg.autolayout
        default_constraints = {}
        default_options = {}
        if autolayout_cfg is not None:
            default_constraints = dict(autolayout_cfg.constraints)
            default_options = {
                "objective": autolayout_cfg.objective,
                "candidate_count": autolayout_cfg.candidate_count,
            }

        return ResolvedAutolayoutTargetFiles(
            project_root=project_path,
            build_target=build_target,
            layout_path=layout_path,
            deeppcb_path=deeppcb_path,
            kicad_project_path=kicad_project_path,
            schematic_path=schematic_path,
            work_root=build_cfg.paths.output_base.parent / "autolayout",
            default_constraints=default_constraints,
            default_options=default_options,
        )

    def _prepare_provider_input(
        self,
        work_dir: Path,
        layout_path: Path,
        deeppcb_path: Path | None,
    ) -> Path:
        if deeppcb_path is not None and deeppcb_path.exists():
            return deeppcb_path

        generated_path = work_dir / "input" / f"{layout_path.stem}.deeppcb"
        generated_path.parent.mkdir(parents=True, exist_ok=True)
        parsed = kicad.loads(kicad.pcb.PcbFile, layout_path)
        board = DeepPCB_Transformer.from_kicad_file(parsed)
        DeepPCB_Transformer.dumps(board, generated_path)
        return generated_path

    def _prepare_input_package(
        self,
        work_dir: Path,
        layout_path: Path,
        kicad_project_path: Path | None,
        schematic_path: Path | None,
        constraints: dict[str, Any],
    ) -> Path:
        package_root = work_dir / "input"
        package_root.mkdir(parents=True, exist_ok=True)

        copied_paths: list[Path] = []
        for path in [layout_path, kicad_project_path, schematic_path]:
            if path is None:
                continue
            destination = package_root / path.name
            shutil.copy2(path, destination)
            copied_paths.append(destination)

        constraints_path = package_root / "autolayout_constraints.json"
        constraints_path.write_text(
            json.dumps(constraints, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        copied_paths.append(constraints_path)

        zip_path = work_dir / "input_bundle.zip"
        with zipfile.ZipFile(
            zip_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            for path in copied_paths:
                archive.write(path, arcname=path.name)

        return zip_path

    def _apply_layout(
        self,
        target_layout_path: Path,
        source_layout_path: Path,
        job_id: str,
    ) -> Path | None:
        target_layout_path.parent.mkdir(parents=True, exist_ok=True)

        backup_path: Path | None = None
        if target_layout_path.exists():
            backup_dir = target_layout_path.parent / "autolayout_backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / (
                f"{target_layout_path.stem}.{job_id}."
                f"{utc_now_iso().replace(':', '')}.kicad_pcb"
            )
            shutil.copy2(target_layout_path, backup_path)

        shutil.copy2(source_layout_path, target_layout_path)
        return backup_path

    def _ensure_enabled(self) -> None:
        if self._settings.enable_autolayout:
            return
        raise RuntimeError("Autolayout is disabled via ATO_ENABLE_AUTOLAYOUT")

    def _emit_job_event(self, job: AutolayoutJob) -> None:
        event_bus.emit_sync(
            "autolayout_changed",
            {
                "jobId": job.job_id,
                "state": job.state.value,
                "projectRoot": job.project_root,
                "buildTarget": job.build_target,
            },
        )


def _dedupe_candidates(
    candidates: list[AutolayoutCandidate],
) -> list[AutolayoutCandidate]:
    seen: set[str] = set()
    deduped: list[AutolayoutCandidate] = []
    for candidate in candidates:
        if candidate.candidate_id in seen:
            continue
        seen.add(candidate.candidate_id)
        deduped.append(candidate)
    return deduped


_AUTOLAYOUT_SERVICE = AutolayoutService()


def get_autolayout_service() -> AutolayoutService:
    """Return process-global autolayout service instance."""

    return _AUTOLAYOUT_SERVICE
