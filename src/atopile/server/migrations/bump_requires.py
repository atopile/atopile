"""Bump the requires-atopile field in ato.yaml."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from ._base import MigrationStep, Topics

log = logging.getLogger(__name__)


class BumpRequiresAtopile(MigrationStep):
    label = "Bump requires-atopile version"
    description = (
        "Updates the requires-atopile field in your ato.yaml to match "
        "the current atopile version."
    )
    topic = Topics.project_config
    order = 0

    async def run(self, project_path: Path) -> None:
        from atopile import version as ato_version
        from atopile.server.domains import projects as projects_domain

        def _do():
            current_version = ato_version.clean_version(
                ato_version.get_installed_atopile_version()
            )
            new_requires = f"^{current_version}"
            data, ato_file = projects_domain.load_ato_yaml(project_path)
            data["requires-atopile"] = new_requires
            projects_domain.save_ato_yaml(ato_file, data)
            log.info("[migrate] Updated requires-atopile to %s", new_requires)

        await asyncio.to_thread(_do)
