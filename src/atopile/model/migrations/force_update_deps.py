"""Force update all project dependencies."""

from __future__ import annotations

import asyncio
from pathlib import Path

from ._base import MigrationStep, Topics


class ForceUpdateDeps(MigrationStep):
    label = "Force update dependencies"
    description = (
        "Downloads the latest compatible versions of all project dependencies. "
        "This can take a few minutes depending on the number of packages."
    )
    topic = Topics.mandatory
    mandatory = True
    order = 0

    async def run(self, project_path: Path) -> None:
        from atopile.config import config
        from faebryk.libs.project.dependencies import ProjectDependencies

        def _do():
            config.apply_options(None, working_dir=project_path)
            ProjectDependencies(
                sync_versions=True,
                install_missing=True,
                clean_unmanaged_dirs=True,
                update_versions=True,
                force_sync=True,
            )

        await asyncio.to_thread(_do)
