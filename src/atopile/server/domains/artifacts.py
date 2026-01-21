"""Artifact (BOM/variables) endpoints."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(tags=["artifacts"])


@router.get("/api/bom")
async def get_bom(
    project_root: str = Query(
        ..., description="Path to the project root (containing ato.yaml)"
    ),
    target: str = Query("default", description="Build target name"),
):
    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Project path does not exist: {project_root}",
        )

    if not (project_path / "ato.yaml").exists():
        raise HTTPException(
            status_code=400,
            detail=f"No ato.yaml found in: {project_root}",
        )

    bom_path = project_path / "build" / "builds" / target / f"{target}.bom.json"

    if not bom_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"BOM file not found: {bom_path}. Run 'ato build' first.",
        )

    try:
        return json.loads(bom_path.read_text())
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in BOM: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/bom/targets")
async def get_bom_targets(
    project_root: str = Query(
        ..., description="Path to the project root (containing ato.yaml)"
    )
):
    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Project path does not exist: {project_root}",
        )

    builds_dir = project_path / "build" / "builds"
    if not builds_dir.exists():
        return {"targets": [], "project_root": project_root}

    targets = []
    for target_dir in builds_dir.iterdir():
        if not target_dir.is_dir():
            continue
        bom_path = target_dir / f"{target_dir.name}.bom.json"
        if bom_path.exists():
            targets.append(target_dir.name)

    return {"targets": targets, "project_root": project_root}


@router.get("/api/variables")
async def get_variables(
    project_root: str = Query(
        ..., description="Path to the project root (containing ato.yaml)"
    ),
    target: str = Query("default", description="Build target name"),
):
    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Project path does not exist: {project_root}",
        )

    if not (project_path / "ato.yaml").exists():
        raise HTTPException(
            status_code=400,
            detail=f"No ato.yaml found in: {project_root}",
        )

    variables_path = (
        project_path / "build" / "builds" / target / f"{target}.variables.json"
    )

    if not variables_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Variables file not found: {variables_path}. Run build first.",
        )

    try:
        return json.loads(variables_path.read_text())
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid JSON: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/variables/targets")
async def get_variables_targets(
    project_root: str = Query(
        ..., description="Path to the project root (containing ato.yaml)"
    )
):
    project_path = Path(project_root)
    if not project_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Project path does not exist: {project_root}",
        )

    builds_dir = project_path / "build" / "builds"
    if not builds_dir.exists():
        return {"targets": [], "project_root": project_root}

    targets = []
    for target_dir in builds_dir.iterdir():
        if not target_dir.is_dir():
            continue
        variables_path = target_dir / f"{target_dir.name}.variables.json"
        if variables_path.exists():
            targets.append(target_dir.name)

    return {"targets": targets, "project_root": project_root}
