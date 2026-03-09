from __future__ import annotations

import json
import logging
import shutil
import struct
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Board3DModel:
    step_path: Path
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
            self.step_path,
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
        self.verify_meshopt_compression()

    @staticmethod
    def _optimizer_command() -> list[str]:
        native = shutil.which("gltfpack")
        if native:
            return [native]
        return ["bun", "x", "gltfpack"]

    def verify_meshopt_compression(self) -> None:
        metadata = self._read_glb_json_chunk(self.glb_path)
        extensions_used = set(metadata.get("extensionsUsed", []))
        if "EXT_meshopt_compression" not in extensions_used:
            raise RuntimeError(
                "Demo GLB optimization did not produce EXT_meshopt_compression: "
                f"{self.glb_path}"
            )

    @staticmethod
    def _read_glb_json_chunk(glb_path: Path) -> dict:
        payload = glb_path.read_bytes()
        if len(payload) < 20:
            raise RuntimeError(f"GLB is too small to parse: {glb_path}")

        magic, version, declared_length = struct.unpack_from("<4sII", payload, 0)
        if magic != b"glTF":
            raise RuntimeError(f"Invalid GLB magic header: {glb_path}")
        if version != 2:
            raise RuntimeError(f"Unsupported GLB version {version}: {glb_path}")
        if declared_length != len(payload):
            raise RuntimeError(
                f"GLB length header mismatch for {glb_path}: "
                f"header={declared_length} actual={len(payload)}"
            )

        offset = 12
        while offset + 8 <= len(payload):
            chunk_length, chunk_type = struct.unpack_from("<II", payload, offset)
            offset += 8
            chunk_end = offset + chunk_length
            if chunk_end > len(payload):
                raise RuntimeError(f"Corrupt GLB chunk table: {glb_path}")
            if chunk_type == 0x4E4F534A:
                return json.loads(payload[offset:chunk_end].decode("utf-8"))
            offset = chunk_end

        raise RuntimeError(f"GLB JSON chunk missing: {glb_path}")
