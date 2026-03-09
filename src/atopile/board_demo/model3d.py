from __future__ import annotations

import logging
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Board3DModel:
    source_glb_path: Path
    pcb_path: Path
    summary_path: Path
    glb_path: Path

    def build_demo_model(
        self,
        *,
        frontend_dir: Path,
    ) -> None:
        self.verify_inputs()
        self.optimize_demo_glb(frontend_dir)

    def verify_inputs(self) -> None:
        required = [
            self.source_glb_path,
            self.pcb_path,
            self.summary_path,
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise RuntimeError(
                "ato demo could not find required build artifacts:\n"
                + "\n".join(missing)
            )

    def optimize_demo_glb(self, frontend_dir: Path) -> None:
        now = time.monotonic()
        command = self._optimizer_command()
        subprocess.run(
            [
                *command,
                "-i",
                str(self.source_glb_path.resolve()),
                "-o",
                str(self.glb_path.resolve()),
                "-c",
            ],
            cwd=str(frontend_dir),
            check=True,
        )
        duration = time.monotonic() - now
        logger.info(
            "Optimized GLB with %s in %.0fms",
            " ".join(command),
            duration * 1000,
        )

    @staticmethod
    def _optimizer_command() -> list[str]:
        native = shutil.which("gltfpack")
        if native:
            return [native]
        return ["bun", "x", "gltfpack"]
