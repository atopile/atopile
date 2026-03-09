from __future__ import annotations

import json
import logging
import struct
import subprocess
import tempfile
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
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            stages = [
                ("dedup", self.source_glb_path, tmpdir_path / "1.glb"),
                ("instance", tmpdir_path / "1.glb", tmpdir_path / "2.glb"),
                ("weld", tmpdir_path / "2.glb", tmpdir_path / "3.glb"),
                ("prune", tmpdir_path / "3.glb", tmpdir_path / "4.glb"),
                ("join", tmpdir_path / "4.glb", tmpdir_path / "5.glb"),
                ("meshopt", tmpdir_path / "5.glb", self.glb_path),
            ]
            for command, src, dst in stages:
                now = time.monotonic()
                subprocess.run(
                    [
                        "bun",
                        "x",
                        "@gltf-transform/cli",
                        command,
                        str(src),
                        str(dst),
                    ],
                    cwd=str(frontend_dir),
                    check=True,
                )
                duration = time.monotonic() - now
                logger.info(f"Optimized ({command}) in {duration * 1000:.0f}ms")
        self.verify_meshopt_compression()

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
