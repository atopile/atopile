"""Rename has_single_electric_reference_shared → has_single_electric_reference."""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

from ._base import MigrationStep, Topic

log = logging.getLogger(__name__)


class RenameReference(MigrationStep):
    label = "Rename has_single_electric_reference_shared"
    description = (
        "Renames the deprecated has_single_electric_reference_shared trait "
        "to match the updated API."
    )
    topic = Topic.ato_language
    order = 10

    async def run(self, project_path: Path) -> None:
        def _do():
            for ato_file in project_path.rglob("*.ato"):
                try:
                    content = ato_file.read_text()
                    new_content = re.sub(
                        r"\bhas_single_electric_reference_shared\b",
                        "has_single_electric_reference",
                        content,
                    )
                    new_content = re.sub(
                        r"\bgnd_only\b",
                        "ground_only",
                        new_content,
                    )
                    if new_content != content:
                        self.atomic_write(ato_file, new_content)
                        log.info(
                            "[migrate] Updated %s: reference trait renames",
                            ato_file,
                        )
                except Exception as exc:
                    log.warning("[migrate] Failed to process %s: %s", ato_file, exc)

        await asyncio.to_thread(_do)
