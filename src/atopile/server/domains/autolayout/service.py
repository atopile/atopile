"""Autolayout service orchestration for provider-backed AI layout."""

from __future__ import annotations

import copy
import json
import shutil
import threading
import uuid
import zipfile
from pathlib import Path
from typing import Any

from atopile.config import ProjectConfig
from atopile.server.domains.autolayout.models import (
    AutolayoutCandidate,
    AutolayoutJob,
    AutolayoutState,
    SubmitRequest,
    utc_now_iso,
)
from atopile.server.domains.autolayout.providers import (
    AutolayoutProvider,
    DeepPCBProvider,
    MockAutolayoutProvider,
    QuilterManualProvider,
)
from atopile.server.events import event_bus
from faebryk.libs.paths import get_log_dir
from faebryk.libs.util import ConfigFlag

_ENABLE_AUTOLAYOUT = ConfigFlag(
    "ENABLE_AUTOLAYOUT", True, "Enable/disable autolayout feature"
)
_DEFAULT_PROVIDER = ConfigFlag(
    "AUTOLAYOUT_PROVIDER", "deeppcb", "Default autolayout provider"
)


class AutolayoutService:
    """Coordinates provider submission, polling, candidate selection, and apply."""

    def __init__(
        self,
        providers: dict[str, AutolayoutProvider] | None = None,
        state_path: str | Path | None = None,
        max_persisted_jobs: int = 200,
    ) -> None:
        self._providers = providers or _default_providers()
        self._jobs: dict[str, AutolayoutJob] = {}
        self._lock = threading.RLock()
        self._state_path = (
            Path(state_path)
            if state_path is not None
            else get_log_dir() / "autolayout_jobs_state.json"
        )
        self._max_persisted_jobs = max(20, int(max_persisted_jobs))
        self._load_jobs_state()

    def start_job(
        self,
        project_root: str,
        build_target: str,
        provider_name: str | None = None,
        constraints: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> AutolayoutJob:
        self._ensure_enabled()

        target_files = self._resolve_target_files(project_root, build_target)

        resolved_provider = (
            provider_name
            or target_files["default_provider"]
            or _DEFAULT_PROVIDER.get()
            or "mock"
        )
        provider = self._provider(resolved_provider)

        job_id = f"al-{uuid.uuid4().hex[:12]}"
        work_dir = target_files["work_root"] / job_id
        work_dir.mkdir(parents=True, exist_ok=True)

        merged_constraints = target_files["default_constraints"]
        if constraints:
            merged_constraints.update(constraints)

        merged_options = target_files["default_options"]
        if options:
            merged_options.update(options)

        zip_path = self._prepare_input_package(
            work_dir=work_dir,
            layout_path=target_files["layout_path"],
            kicad_project_path=target_files["kicad_project_path"],
            schematic_path=target_files["schematic_path"],
            constraints=merged_constraints,
        )

        job = AutolayoutJob(
            job_id=job_id,
            project_root=str(target_files["project_root"]),
            build_target=build_target,
            provider=provider.name,
            state=AutolayoutState.QUEUED,
            created_at=utc_now_iso(),
            updated_at=utc_now_iso(),
            constraints=merged_constraints,
            options=merged_options,
            input_zip_path=str(zip_path),
            work_dir=str(work_dir),
            layout_path=str(target_files["layout_path"]),
        )

        with self._lock:
            self._jobs[job_id] = job
            self._persist_jobs_state_locked()

        try:
            submit_result = provider.submit(
                SubmitRequest(
                    job_id=job_id,
                    project_root=Path(job.project_root),
                    build_target=build_target,
                    layout_path=Path(job.layout_path),
                    input_zip_path=zip_path,
                    work_dir=work_dir,
                    constraints=merged_constraints,
                    options=merged_options,
                    kicad_project_path=target_files["kicad_project_path"],
                    schematic_path=target_files["schematic_path"],
                )
            )
        except Exception as exc:
            with self._lock:
                current = self._jobs[job_id]
                current.state = AutolayoutState.FAILED
                current.error = str(exc)
                current.message = str(exc)
                current.mark_updated()
                self._persist_jobs_state_locked()
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
            self._persist_jobs_state_locked()
            self._emit_job_event(current)
            return copy.deepcopy(current)

    def get_job(self, job_id: str) -> AutolayoutJob:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(f"Unknown autolayout job: {job_id}")
            return copy.deepcopy(job)

    def list_jobs(self, project_root: str | None = None) -> list[AutolayoutJob]:
        with self._lock:
            values = list(self._jobs.values())

        if project_root is not None:
            values = [job for job in values if job.project_root == project_root]

        values.sort(key=lambda job: job.created_at, reverse=True)
        return [copy.deepcopy(job) for job in values]

    def recover_job(
        self,
        project_root: str,
        job_id: str,
        build_target_hint: str | None = None,
    ) -> AutolayoutJob | None:
        with self._lock:
            cached = self._jobs.get(job_id)
            if cached is not None:
                return copy.deepcopy(cached)

        project_path = Path(project_root).resolve()
        project_cfg = ProjectConfig.from_path(project_path)
        if project_cfg is None:
            return None

        build_order = list(project_cfg.builds.keys())
        if build_target_hint and build_target_hint in project_cfg.builds:
            build_order = [build_target_hint] + [
                target for target in build_order if target != build_target_hint
            ]

        for build_target in build_order:
            build_cfg = project_cfg.builds[build_target]
            work_dir = build_cfg.paths.output_base.parent / "autolayout" / job_id
            if not work_dir.exists() or not work_dir.is_dir():
                continue

            provider_name = (
                build_cfg.autolayout.provider
                if build_cfg.autolayout is not None
                else _DEFAULT_PROVIDER.get() or "deeppcb"
            )
            if provider_name not in self._providers:
                provider_name = "deeppcb" if "deeppcb" in self._providers else "mock"

            downloads_dir = work_dir / "downloads"
            candidates = self._discover_local_candidates(downloads_dir)

            now_iso = utc_now_iso()
            job = AutolayoutJob(
                job_id=job_id,
                project_root=str(project_path),
                build_target=build_target,
                provider=provider_name,
                state=(
                    AutolayoutState.AWAITING_SELECTION
                    if candidates
                    else AutolayoutState.RUNNING
                ),
                created_at=now_iso,
                updated_at=now_iso,
                input_zip_path=(
                    str(work_dir / "input_bundle.zip")
                    if (work_dir / "input_bundle.zip").exists()
                    else None
                ),
                work_dir=str(work_dir),
                layout_path=str(build_cfg.paths.layout),
                candidates=candidates,
                message=(
                    "Recovered from local autolayout artifacts."
                    if candidates
                    else "Recovered autolayout job (no local candidates found)."
                ),
            )
            resolved_provider_ref = self._resolve_provider_job_ref(
                job=job,
                provider=self._providers[job.provider],
            )
            if isinstance(resolved_provider_ref, str) and resolved_provider_ref.strip():
                job.provider_job_ref = resolved_provider_ref.strip()

            with self._lock:
                self._jobs[job_id] = job
                self._persist_jobs_state_locked()
                self._emit_job_event(job)
                return copy.deepcopy(job)

        return None

    def recover_project_jobs(
        self,
        project_root: str,
        limit: int = 20,
    ) -> list[AutolayoutJob]:
        project_path = Path(project_root).resolve()
        project_cfg = ProjectConfig.from_path(project_path)
        if project_cfg is None:
            return []

        discovered: list[tuple[float, str, str]] = []
        for build_target, build_cfg in project_cfg.builds.items():
            work_root = build_cfg.paths.output_base.parent / "autolayout"
            if not work_root.exists() or not work_root.is_dir():
                continue
            for child in work_root.iterdir():
                if not child.is_dir() or not child.name.startswith("al-"):
                    continue
                try:
                    mtime = child.stat().st_mtime
                except OSError:
                    continue
                discovered.append((mtime, build_target, child.name))

        discovered.sort(key=lambda item: item[0], reverse=True)
        recovered: list[AutolayoutJob] = []
        for _, build_target, job_id in discovered[: max(1, int(limit))]:
            job = self.recover_job(
                project_root=str(project_path),
                job_id=job_id,
                build_target_hint=build_target,
            )
            if job is not None:
                recovered.append(job)

        recovered.sort(key=lambda job: job.updated_at, reverse=True)
        return recovered

    def refresh_job(self, job_id: str) -> AutolayoutJob:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(f"Unknown autolayout job: {job_id}")
            if (
                job.state in {AutolayoutState.FAILED, AutolayoutState.CANCELLED}
            ):
                return copy.deepcopy(job)
            provider = self._providers[job.provider]
            if not provider.capabilities.supports_candidates:
                return copy.deepcopy(job)
            provider_job_ref = job.provider_job_ref

        if not provider_job_ref:
            recovered_ref = self._resolve_provider_job_ref(job, provider)
            if not recovered_ref:
                return copy.deepcopy(job)
            with self._lock:
                current = self._jobs.get(job_id)
                if current is None:
                    raise KeyError(f"Unknown autolayout job: {job_id}")
                current.provider_job_ref = recovered_ref
                current.mark_updated()
                self._persist_jobs_state_locked()
                self._emit_job_event(current)
                provider_job_ref = recovered_ref

        try:
            status = provider.status(provider_job_ref)
        except Exception as exc:
            with self._lock:
                current = self._jobs[job_id]
                current.state = AutolayoutState.FAILED
                current.error = str(exc)
                current.message = str(exc)
                current.mark_updated()
                self._persist_jobs_state_locked()
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
            self._persist_jobs_state_locked()
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

        provider = self._provider(job.provider)
        candidates = provider.list_candidates(job.provider_job_ref)

        with self._lock:
            current = self._jobs[job_id]
            current.candidates = _dedupe_candidates(candidates)
            if current.candidates and current.state == AutolayoutState.COMPLETED:
                current.state = AutolayoutState.AWAITING_SELECTION
            current.mark_updated()
            self._persist_jobs_state_locked()
            self._emit_job_event(current)
            return [copy.deepcopy(candidate) for candidate in current.candidates]

    def select_candidate(self, job_id: str, candidate_id: str) -> AutolayoutJob:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(f"Unknown autolayout job: {job_id}")

            if not any(c.candidate_id == candidate_id for c in job.candidates):
                raise KeyError(
                    f"Unknown candidate '{candidate_id}' for autolayout job '{job_id}'"
                )

            job.selected_candidate_id = candidate_id
            job.mark_updated()
            self._persist_jobs_state_locked()
            self._emit_job_event(job)
            return copy.deepcopy(job)

    def apply_candidate(
        self,
        job_id: str,
        candidate_id: str | None = None,
        manual_layout_path: str | None = None,
    ) -> AutolayoutJob:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(f"Unknown autolayout job: {job_id}")

            selected_candidate_id = candidate_id or job.selected_candidate_id
            provider = self._providers[job.provider]
            if selected_candidate_id is None and manual_layout_path is None:
                raise ValueError("No candidate selected")
            provider_job_ref = job.provider_job_ref
            layout_path = Path(job.layout_path or "")

        if manual_layout_path:
            downloaded_layout = Path(manual_layout_path)
            if not downloaded_layout.exists():
                raise FileNotFoundError(
                    f"Manual layout candidate file not found: {downloaded_layout}"
                )
            chosen_candidate = selected_candidate_id or "manual"
        else:
            assert selected_candidate_id is not None
            if not provider_job_ref:
                local_layout = self._resolve_local_candidate_layout(
                    job=job,
                    candidate_id=selected_candidate_id,
                )
                if local_layout is None:
                    raise RuntimeError(
                        "Provider job reference missing and no local candidate "
                        f"artifact found for '{selected_candidate_id}'."
                    )
                downloaded_layout = local_layout
            else:
                download_result = provider.download_candidate(
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
            self._persist_jobs_state_locked()
            self._emit_job_event(current)
            return copy.deepcopy(current)

    def cancel_job(self, job_id: str) -> AutolayoutJob:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(f"Unknown autolayout job: {job_id}")
            provider = self._providers[job.provider]
            provider_job_ref = job.provider_job_ref

        if provider_job_ref and provider.capabilities.supports_cancel:
            provider.cancel(provider_job_ref)

        with self._lock:
            current = self._jobs[job_id]
            current.state = AutolayoutState.CANCELLED
            current.mark_updated()
            self._persist_jobs_state_locked()
            self._emit_job_event(current)
            return copy.deepcopy(current)

    def export_quilter_package(self, project_root: str, build_target: str) -> str:
        target_files = self._resolve_target_files(project_root, build_target)
        package_dir = target_files["work_root"] / "quilter_manual"
        package_dir.mkdir(parents=True, exist_ok=True)

        zip_path = self._prepare_input_package(
            work_dir=package_dir,
            layout_path=target_files["layout_path"],
            kicad_project_path=target_files["kicad_project_path"],
            schematic_path=target_files["schematic_path"],
            constraints=target_files["default_constraints"],
        )
        return str(zip_path)

    def _resolve_target_files(
        self,
        project_root: str,
        build_target: str,
    ) -> dict[str, Any]:
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
        default_provider: str | None = None
        if autolayout_cfg is not None:
            default_constraints = dict(autolayout_cfg.constraints)
            default_options = {
                "objective": autolayout_cfg.objective,
                "candidate_count": autolayout_cfg.candidate_count,
            }
            default_provider = autolayout_cfg.provider

        return {
            "project_root": project_path,
            "build_target": build_target,
            "layout_path": layout_path,
            "kicad_project_path": kicad_project_path,
            "schematic_path": schematic_path,
            "work_root": build_cfg.paths.output_base.parent / "autolayout",
            "default_constraints": default_constraints,
            "default_options": default_options,
            "default_provider": default_provider,
        }

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
            _json_dumps(constraints),
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

    def _persist_jobs_state_locked(self) -> None:
        jobs_sorted = sorted(
            self._jobs.values(),
            key=lambda job: job.updated_at,
            reverse=True,
        )[: self._max_persisted_jobs]
        payload = {
            "version": 1,
            "saved_at": utc_now_iso(),
            "jobs": [job.to_dict() for job in jobs_sorted],
        }

        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self._state_path.with_suffix(
                f"{self._state_path.suffix}.tmp"
            )
            tmp_path.write_text(_json_dumps(payload), encoding="utf-8")
            tmp_path.replace(self._state_path)
        except OSError:
            # Persistence failures must never break active autolayout jobs.
            return

    def _load_jobs_state(self) -> None:
        try:
            raw = self._state_path.read_text(encoding="utf-8")
        except OSError:
            return

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return
        if not isinstance(payload, dict):
            return
        raw_jobs = payload.get("jobs")
        if not isinstance(raw_jobs, list):
            return

        restored: dict[str, AutolayoutJob] = {}
        for raw_job in raw_jobs:
            if not isinstance(raw_job, dict):
                continue
            job = _deserialize_autolayout_job(raw_job)
            if job is None:
                continue
            if job.provider not in self._providers:
                continue
            restored[job.job_id] = job

        if not restored:
            return

        with self._lock:
            self._jobs.update(restored)

    def _discover_local_candidates(self, downloads_dir: Path) -> list[AutolayoutCandidate]:
        if not downloads_dir.exists() or not downloads_dir.is_dir():
            return []

        candidates: list[tuple[float, AutolayoutCandidate]] = []
        for path in downloads_dir.glob("*.kicad_pcb"):
            if not path.is_file():
                continue
            candidate_id = path.stem.strip()
            if not candidate_id:
                continue
            try:
                mtime = path.stat().st_mtime
            except OSError:
                mtime = 0.0
            candidates.append(
                (
                    mtime,
                    AutolayoutCandidate(
                        candidate_id=candidate_id,
                        label=f"Local {candidate_id}",
                        metadata={"source": "local_download"},
                        files={"kicad_pcb": str(path)},
                    ),
                )
            )

        candidates.sort(key=lambda item: item[0], reverse=True)
        return _dedupe_candidates([candidate for _, candidate in candidates])

    def _resolve_local_candidate_layout(
        self,
        *,
        job: AutolayoutJob,
        candidate_id: str,
    ) -> Path | None:
        for candidate in job.candidates:
            if candidate.candidate_id != candidate_id:
                continue
            path_raw = candidate.files.get("kicad_pcb")
            if isinstance(path_raw, str) and path_raw.strip():
                path = Path(path_raw)
                if path.exists():
                    return path

        work_dir_raw = str(job.work_dir or "").strip()
        if not work_dir_raw:
            return None
        downloads_dir = Path(work_dir_raw) / "downloads"
        if not downloads_dir.exists():
            return None

        preferred = downloads_dir / f"{candidate_id}.kicad_pcb"
        if preferred.exists():
            return preferred

        matches = sorted(
            downloads_dir.glob("*.kicad_pcb"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if matches:
            return matches[0]
        return None

    def _resolve_provider_job_ref(
        self,
        job: AutolayoutJob,
        provider: AutolayoutProvider,
    ) -> str | None:
        current = str(job.provider_job_ref or "").strip()
        if current:
            return current

        resolver = getattr(provider, "_resolve_board_ids_single", None)
        if not callable(resolver):
            return None

        try:
            resolved = resolver(job.job_id)
        except Exception:
            return None

        if not isinstance(resolved, list):
            return None
        for value in resolved:
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _provider(self, provider_name: str) -> AutolayoutProvider:
        provider = self._providers.get(provider_name)
        if provider is None:
            available = ", ".join(sorted(self._providers.keys()))
            raise KeyError(
                f"Unknown autolayout provider '{provider_name}'. Available: {available}"
            )
        return provider

    def _ensure_enabled(self) -> None:
        if _ENABLE_AUTOLAYOUT.get():
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


def _default_providers() -> dict[str, AutolayoutProvider]:
    return {
        "mock": MockAutolayoutProvider(),
        "quilter_manual": QuilterManualProvider(),
        "deeppcb": DeepPCBProvider(),
    }


def _json_dumps(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True)


def _deserialize_autolayout_job(payload: dict[str, Any]) -> AutolayoutJob | None:
    job_id = payload.get("job_id")
    project_root = payload.get("project_root")
    build_target = payload.get("build_target")
    provider = payload.get("provider")
    if not all(isinstance(value, str) and value.strip() for value in (
        job_id,
        project_root,
        build_target,
        provider,
    )):
        return None

    state_raw = payload.get("state")
    try:
        state = AutolayoutState(str(state_raw))
    except ValueError:
        state = AutolayoutState.QUEUED

    raw_candidates = payload.get("candidates")
    candidates: list[AutolayoutCandidate] = []
    if isinstance(raw_candidates, list):
        for raw_candidate in raw_candidates:
            if not isinstance(raw_candidate, dict):
                continue
            candidate_id = raw_candidate.get("candidate_id")
            if not isinstance(candidate_id, str) or not candidate_id.strip():
                continue
            metadata = raw_candidate.get("metadata")
            files = raw_candidate.get("files")
            candidates.append(
                AutolayoutCandidate(
                    candidate_id=candidate_id.strip(),
                    label=(
                        str(raw_candidate["label"]).strip()
                        if isinstance(raw_candidate.get("label"), str)
                        and str(raw_candidate.get("label")).strip()
                        else None
                    ),
                    score=(
                        float(raw_candidate["score"])
                        if isinstance(raw_candidate.get("score"), (int, float))
                        else None
                    ),
                    metadata=metadata if isinstance(metadata, dict) else {},
                    files=files if isinstance(files, dict) else {},
                )
            )

    created_at = payload.get("created_at")
    updated_at = payload.get("updated_at")
    return AutolayoutJob(
        job_id=job_id.strip(),
        project_root=project_root.strip(),
        build_target=build_target.strip(),
        provider=provider.strip(),
        state=state,
        created_at=(
            created_at
            if isinstance(created_at, str) and created_at.strip()
            else utc_now_iso()
        ),
        updated_at=(
            updated_at
            if isinstance(updated_at, str) and updated_at.strip()
            else utc_now_iso()
        ),
        provider_job_ref=(
            payload["provider_job_ref"].strip()
            if isinstance(payload.get("provider_job_ref"), str)
            and payload["provider_job_ref"].strip()
            else None
        ),
        progress=(
            float(payload["progress"])
            if isinstance(payload.get("progress"), (int, float))
            else None
        ),
        message=payload.get("message")
        if isinstance(payload.get("message"), str)
        else None,
        error=payload.get("error") if isinstance(payload.get("error"), str) else None,
        constraints=(
            dict(payload["constraints"])
            if isinstance(payload.get("constraints"), dict)
            else {}
        ),
        options=(
            dict(payload["options"]) if isinstance(payload.get("options"), dict) else {}
        ),
        input_zip_path=payload.get("input_zip_path")
        if isinstance(payload.get("input_zip_path"), str)
        else None,
        work_dir=payload.get("work_dir")
        if isinstance(payload.get("work_dir"), str)
        else None,
        layout_path=payload.get("layout_path")
        if isinstance(payload.get("layout_path"), str)
        else None,
        selected_candidate_id=payload.get("selected_candidate_id")
        if isinstance(payload.get("selected_candidate_id"), str)
        else None,
        applied_candidate_id=payload.get("applied_candidate_id")
        if isinstance(payload.get("applied_candidate_id"), str)
        else None,
        applied_layout_path=payload.get("applied_layout_path")
        if isinstance(payload.get("applied_layout_path"), str)
        else None,
        backup_layout_path=payload.get("backup_layout_path")
        if isinstance(payload.get("backup_layout_path"), str)
        else None,
        candidates=_dedupe_candidates(candidates),
    )


_AUTOLAYOUT_SERVICE = AutolayoutService()


def get_autolayout_service() -> AutolayoutService:
    """Return process-global autolayout service instance."""

    return _AUTOLAYOUT_SERVICE
