"""Graph-first datasheet collection for server features."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from atopile import build_steps
from atopile.buildutil import BuildStepContext
from atopile.config import config
from faebryk.exporters.documentation.datasheets import export_datasheets


def _normalize_lcsc_id(raw: str | None) -> str | None:
    if not raw:
        return None
    token = raw.strip().upper()
    if not token:
        return None
    if token.startswith("C"):
        number = token[1:]
    else:
        number = token
        token = f"C{token}"
    if not number.isdigit():
        return None
    return token


def _resolve_build_target(build_target: str | None) -> str:
    available = list(config.project.builds.keys())
    if not available:
        raise ValueError("No build targets found in project config")

    if build_target:
        cleaned = build_target.strip()
        if cleaned in config.project.builds:
            return cleaned
        raise ValueError(f"Build target not found: {build_target}")

    if "default" in config.project.builds:
        return "default"
    return available[0]


def handle_collect_project_datasheets(
    project_root: str,
    *,
    build_target: str | None = None,
    lcsc_ids: list[str] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    project_path = Path(project_root).expanduser().resolve()
    if not project_path.exists():
        raise ValueError(f"Project root does not exist: {project_root}")

    config.apply_options(
        None,
        working_dir=project_path,
        selected_builds=[build_target] if build_target else [],
    )
    resolved_target = _resolve_build_target(build_target)
    normalized_lcsc_ids = sorted(
        {
            normalized
            for normalized in (
                _normalize_lcsc_id(value)
                for value in (lcsc_ids or [])
            )
            if normalized
        }
    )

    with config.select_build(resolved_target):
        ctx = BuildStepContext(build=None, app=None)
        for target in build_steps.muster.select({"post-instantiation-setup"}):
            target(ctx)
        app = ctx.require_app()
        output_dir = config.build.paths.documentation / "datasheets"
        exported = export_datasheets(
            app,
            path=output_dir,
            overwrite=overwrite,
            progress=None,
            lcsc_ids=normalized_lcsc_ids or None,
        )

    normalized_filter = set(normalized_lcsc_ids)
    if normalized_filter:
        matches = [
            item
            for item in exported
            if normalized_filter.intersection(set(item.get("lcsc_ids", [])))
        ]
    else:
        matches = list(exported)

    return {
        "project_root": str(project_path),
        "build_target": resolved_target,
        "directory": str(output_dir),
        "requested_lcsc_ids": normalized_lcsc_ids,
        "exported": exported,
        "matches": matches,
    }

