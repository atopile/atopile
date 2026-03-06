"""
File serving routes for the build server.

Provides REST endpoints to serve local build output files.
"""

from __future__ import annotations

import logging
import mimetypes
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response, StreamingResponse

from atopile.model.model_state import model_state

log = logging.getLogger(__name__)

router = APIRouter(tags=["files"])


def _get_content_type(path: Path) -> str:
    """Determine content type based on file extension."""
    suffix = path.suffix.lower()

    # Custom mappings for known file types
    custom_types = {
        ".kicad_pcb": "application/x-kicad-pcb",
        ".kicad_sch": "application/x-kicad-schematic",
        ".glb": "model/gltf-binary",
        ".gltf": "model/gltf+json",
        ".step": "model/step",
        ".stp": "model/step",
        ".zip": "application/zip",
        ".json": "application/json",
        ".csv": "text/csv",
        ".gbr": "application/x-gerber",
        ".gbl": "application/x-gerber",
        ".gtl": "application/x-gerber",
        ".gbs": "application/x-gerber",
        ".gts": "application/x-gerber",
        ".gbo": "application/x-gerber",
        ".gto": "application/x-gerber",
        ".drl": "application/x-excellon",
    }

    if suffix in custom_types:
        return custom_types[suffix]

    # Fall back to mimetypes
    mime_type, _ = mimetypes.guess_type(str(path))
    return mime_type or "application/octet-stream"


def _is_path_allowed(file_path: Path) -> bool:
    """
    Check if the file path is allowed to be served.

    Only allows files within:
    - Workspace build directories
    - Standard atopile output directories
    """
    try:
        resolved = file_path.resolve()
    except (OSError, ValueError):
        log.warning(f"[files] Path resolution failed for: {file_path}")
        return False

    # Check if within workspace paths
    workspace_paths = model_state.workspace_paths
    log.info(
        f"[files] Checking path {resolved} against "
        f"{len(workspace_paths)} workspace paths: {workspace_paths}"
    )
    for workspace in workspace_paths:
        try:
            workspace_resolved = workspace.resolve()
            log.info(f"[files] Checking against workspace: {workspace_resolved}")
            if resolved.is_relative_to(workspace_resolved):
                # Only allow files from build directories
                relative = resolved.relative_to(workspace_resolved)
                parts = relative.parts
                log.info(f"[files] Path is relative to workspace, parts: {parts}")
                if "build" in parts:
                    log.info(f"[files] Path allowed via workspace_paths: {resolved}")
                    return True
                else:
                    log.info("[files] Path rejected: 'build' not in parts")
        except (OSError, ValueError) as e:
            log.warning(f"[files] Error checking workspace {workspace}: {e}")
            continue

    # Also check current workspace path
    workspace = model_state.workspace_path
    log.info(f"[files] Checking against current workspace_path: {workspace}")
    if workspace:
        try:
            workspace_resolved = workspace.resolve()
            if resolved.is_relative_to(workspace_resolved):
                relative = resolved.relative_to(workspace_resolved)
                parts = relative.parts
                log.info(
                    f"[files] Path is relative to current workspace, parts: {parts}"
                )
                if "build" in parts:
                    log.info(f"[files] Path allowed via workspace_path: {resolved}")
                    return True
        except (OSError, ValueError):
            pass

    log.warning(
        f"[files] Path not allowed: {resolved}. "
        f"Workspace paths: {workspace_paths}, workspace: {workspace}"
    )
    return False


@router.get("/api/file")
async def get_file(
    path: str = Query(..., description="Absolute path to the file"),
):
    """
    Serve a local file from the build output directory.

    Security: Only files within project build directories are allowed.
    """
    log.info(f"[files] GET /api/file path={path}")

    if not path:
        raise HTTPException(status_code=400, detail="Missing path parameter")

    file_path = Path(path)

    if not file_path.is_absolute():
        log.warning(f"[files] Rejected non-absolute path: {path}")
        raise HTTPException(status_code=400, detail="Path must be absolute")

    if not _is_path_allowed(file_path):
        log.warning(f"[files] Rejected path not in allowed directory: {path}")
        raise HTTPException(
            status_code=403, detail="Access denied: file not in allowed directory"
        )

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    content_type = _get_content_type(file_path)

    # For large files, use streaming response
    file_size = file_path.stat().st_size

    if file_size > 10 * 1024 * 1024:  # 10 MB

        def iter_file():
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk

        return StreamingResponse(
            iter_file(),
            media_type=content_type,
            headers={
                "Content-Disposition": f"inline; filename={file_path.name}",
                "Content-Length": str(file_size),
            },
        )

    # For smaller files, read all at once
    content = file_path.read_bytes()

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f"inline; filename={file_path.name}",
        },
    )


@router.get("/api/file/zip-contents")
async def get_zip_file_contents(
    path: str = Query(..., description="Absolute path to the zip file"),
    entry: str = Query(..., description="Path to the file within the zip"),
):
    """
    Serve a file from within a zip archive.

    Used for serving individual gerber files from gerber.zip archives.
    """
    if not path or not entry:
        raise HTTPException(status_code=400, detail="Missing path or entry parameter")

    file_path = Path(path)

    if not file_path.is_absolute():
        raise HTTPException(status_code=400, detail="Path must be absolute")

    if not _is_path_allowed(file_path):
        raise HTTPException(
            status_code=403, detail="Access denied: file not in allowed directory"
        )

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Zip file not found: {path}")

    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            # Normalize the entry path
            entry_normalized = entry.lstrip("/")

            if entry_normalized not in zf.namelist():
                raise HTTPException(
                    status_code=404,
                    detail=f"Entry not found in zip: {entry}",
                )

            content = zf.read(entry_normalized)
            content_type = _get_content_type(Path(entry_normalized))

            return Response(
                content=content,
                media_type=content_type,
                headers={
                    "Content-Disposition": (
                        f"inline; filename={Path(entry_normalized).name}"
                    ),
                },
            )
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip file")
    except Exception as e:
        log.error(f"Error reading zip file: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading zip file: {e}")


@router.get("/api/file/zip-list")
async def list_zip_contents(
    path: str = Query(..., description="Absolute path to the zip file"),
):
    """
    List the contents of a zip archive.

    Returns a list of file entries in the zip.
    """
    if not path:
        raise HTTPException(status_code=400, detail="Missing path parameter")

    file_path = Path(path)

    if not file_path.is_absolute():
        raise HTTPException(status_code=400, detail="Path must be absolute")

    if not _is_path_allowed(file_path):
        raise HTTPException(
            status_code=403, detail="Access denied: file not in allowed directory"
        )

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Zip file not found: {path}")

    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            entries = []
            for info in zf.infolist():
                if not info.is_dir():
                    entries.append(
                        {
                            "name": info.filename,
                            "size": info.file_size,
                        }
                    )
            return {"entries": entries}
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip file")
    except Exception as e:
        log.error(f"Error reading zip file: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading zip file: {e}")
