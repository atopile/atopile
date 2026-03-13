"""Sanitize KiCad filenames in auto-generated parts.

Renames footprint, symbol, and model files that contain characters
outside [a-zA-Z0-9_] and updates the .ato manifests to match.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from ._base import MigrationStep, Topics

log = logging.getLogger(__name__)


class SanitizePartFilenames(MigrationStep):
    label = "Sanitize part filenames"
    description = (
        "Renames KiCad footprint, symbol and 3D-model files in the parts "
        "directory so they only contain safe characters (a-z, A-Z, 0-9, _)."
    )
    topic = Topics.project_structure
    order = 10

    async def run(self, project_path: Path) -> None:
        from atopile.config import ProjectConfig
        from faebryk.libs.ato_part import AtoPart

        def _do() -> None:
            project_config = ProjectConfig.from_path(project_path)
            if project_config is None:
                return
            parts_dir = project_config.paths.parts

            if not parts_dir.is_dir():
                return

            failed: list[tuple[Path, str]] = []
            migrated = 0

            for part_dir in sorted(parts_dir.iterdir()):
                if not part_dir.is_dir():
                    continue
                try:
                    if AtoPart.migrate_filenames(part_dir):
                        migrated += 1
                except Exception as exc:
                    failed.append((part_dir, str(exc)))
                    log.warning(
                        "[migrate] Failed to sanitize %s: %s", part_dir.name, exc
                    )

            if migrated:
                log.info("[migrate] Sanitized filenames in %d part(s)", migrated)

            if failed:
                names = ", ".join(d.name for d, _ in failed)
                raise RuntimeError(f"Failed to migrate {len(failed)} part(s): {names}")

        await asyncio.to_thread(_do)
