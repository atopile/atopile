from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from atopile.board_demo.model3d import Board3DModel
from atopile.config import config
from faebryk.exporters.pcb.kicad.artifacts import (
    KicadCliExportError,
    export_glb,
    export_pcb_summary,
    githash_layout,
)

log = logging.getLogger(__name__)


@dataclass
class DemoPaths:
    build_name: str
    build_dir: Path
    output_dir: Path
    source_glb_path: Path
    pcb_path: Path
    summary_path: Path
    render_model_path: Path
    glb_path: Path
    screenshot_dir: Path
    manifest_path: Path
    index_path: Path


class DemoBundleBuilder:
    def __init__(self, *, output_dir: Path | None = None) -> None:
        _ensure_tool("bun")
        self.frontend_dir = Path(__file__).parent / "frontend"
        self.paths = self._make_paths(output_dir=output_dir)
        self.model3d = Board3DModel(
            source_glb_path=self.paths.source_glb_path,
            pcb_path=self.paths.pcb_path,
            summary_path=self.paths.summary_path,
            glb_path=self.paths.glb_path,
        )

    def build(self) -> DemoPaths:
        # Start from a clean output directory for the generated demo bundle.
        if self.paths.output_dir.exists():
            shutil.rmtree(self.paths.output_dir)
        self.paths.output_dir.mkdir(parents=True, exist_ok=True)

        # Ensure the KiCad-derived PCB, GLB, and summary inputs exist.
        _ensure_layout_derived_artifacts(
            layout_path=config.build.paths.layout,
            output_base=config.build.paths.output_base,
            model3d=self.model3d,
        )

        # Export the read-only layout render model consumed by the frontend.
        _export_layout_render_model(self.paths.pcb_path, self.paths.render_model_path)

        # Build the optimized 3D board model used by the demo viewer.
        log.info(
            "Building demo 3D model for %s",
            self.paths.build_name,
        )
        self.model3d.build_demo_model(
            frontend_dir=self.frontend_dir,
        )

        # Build the frontend bundle and copy the embed script into the demo output.
        _build_embed_bundle(self.paths, frontend_dir=self.frontend_dir)

        # Write the demo manifest and static HTML entrypoint.
        _write_manifest(self.paths)
        _write_index_html(self.paths)

        # Render screenshots, then rewrite the manifest with the generated poster.
        _validate_with_puppeteer(self.paths, frontend_dir=self.frontend_dir)
        _write_manifest(self.paths, poster_path="poster.png")
        return self.paths

    def _make_paths(self, *, output_dir: Path | None) -> DemoPaths:
        build_name = config.build.name
        build_dir = config.build.paths.output_base.parent
        demo_dir = output_dir or (build_dir / "demo")
        return DemoPaths(
            build_name=build_name,
            build_dir=build_dir,
            output_dir=demo_dir,
            source_glb_path=config.build.paths.output_base.with_suffix(".pcba.glb"),
            pcb_path=config.build.paths.output_base.with_suffix(".kicad_pcb"),
            summary_path=config.build.paths.output_base.with_suffix(
                ".pcb_summary.json"
            ),
            render_model_path=demo_dir / "layout.render-model.json",
            glb_path=demo_dir / "board.glb",
            screenshot_dir=demo_dir / "screenshots",
            manifest_path=demo_dir / "demo-manifest.json",
            index_path=demo_dir / "index.html",
        )


def build_demo_bundle(*, output_dir: Path | None = None) -> DemoPaths:
    return DemoBundleBuilder(output_dir=output_dir).build()


def _ensure_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required tool not found on PATH: {name}")
    return path


def _ensure_layout_derived_artifacts(
    *,
    layout_path: Path,
    output_base: Path,
    model3d: Board3DModel,
) -> None:
    if not layout_path.exists():
        raise RuntimeError(
            "ato demo requires an existing layout file, but none was found at: "
            f"{layout_path}"
        )

    output_base.parent.mkdir(parents=True, exist_ok=True)

    if not model3d.pcb_path.exists():
        shutil.copy2(layout_path, model3d.pcb_path)

    missing_exports = [
        not model3d.source_glb_path.exists(),
        not model3d.summary_path.exists(),
    ]
    if not any(missing_exports):
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_layout = githash_layout(layout_path, Path(tmpdir) / layout_path.name)
        project_dir = layout_path.parent
        if not model3d.source_glb_path.exists():
            try:
                export_glb(
                    tmp_layout,
                    glb_file=model3d.source_glb_path,
                    project_dir=project_dir,
                )
            except KicadCliExportError as exc:
                raise RuntimeError(f"Failed to generate demo GLB: {exc}") from exc
        if not model3d.summary_path.exists():
            try:
                export_pcb_summary(tmp_layout, summary_file=model3d.summary_path)
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to generate demo PCB summary: {exc}"
                ) from exc


def _export_layout_render_model(pcb_path: Path, output_path: Path) -> None:
    from atopile.layout_server.pcb_manager import PcbManager

    mgr = PcbManager()
    mgr.load(pcb_path)
    model = mgr.get_render_model()
    output_path.write_text(model.model_dump_json(), encoding="utf-8")


def _build_embed_bundle(paths: DemoPaths, *, frontend_dir: Path) -> None:
    _ensure_bun_install(frontend_dir)
    env = os.environ.copy()
    env["ATO_DEMO_OUT_DIR"] = str(paths.output_dir)
    subprocess.run(
        ["bun", "run", "build"],
        cwd=str(frontend_dir),
        env=env,
        check=True,
    )
    dist_dir = frontend_dir / "dist"
    shutil.copy2(dist_dir / "embed.js", paths.output_dir / "embed.js")


def _ensure_bun_install(bundle_dir: Path) -> None:
    node_modules = bundle_dir / "node_modules"
    if node_modules.exists():
        return
    subprocess.run(["bun", "install"], cwd=str(bundle_dir), check=True)


def _write_manifest(paths: DemoPaths, *, poster_path: str | None = None) -> None:
    summary = json.loads(paths.summary_path.read_text(encoding="utf-8"))
    render_model = json.loads(paths.render_model_path.read_text(encoding="utf-8"))
    hidden_layout_layers = [
        layer["id"]
        for layer in render_model.get("layers", [])
        if not layer.get("default_visible", True)
    ]
    manifest: dict[str, Any] = {
        "buildName": paths.build_name,
        "title": f"{paths.build_name} PCB",
        "subtitle": "Read-only layout paired with an interactive 3D assembly preview.",
        "layoutModelPath": paths.render_model_path.name,
        "modelPath": paths.glb_path.name,
        "hiddenLayoutLayers": hidden_layout_layers,
        "screenshotsDir": paths.screenshot_dir.name,
        "summary": summary,
    }
    if poster_path:
        manifest["posterPath"] = poster_path
    paths.manifest_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )


def _write_index_html(paths: DemoPaths) -> None:
    html = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>atopile demo</title>
  </head>
  <body style="margin:0;background:#0b1119;">
    <div id="app" style="width:100vw;height:100vh;"></div>
    <script src="./embed.js"></script>
    <script>
      window.AtopileDemo.mount(document.getElementById("app"));
    </script>
  </body>
</html>
"""
    paths.index_path.write_text(html, encoding="utf-8")


def _validate_with_puppeteer(paths: DemoPaths, *, frontend_dir: Path) -> None:
    env = os.environ.copy()
    env["ATO_DEMO_SCREENSHOT_DIR"] = str(paths.screenshot_dir)
    subprocess.run(
        [
            "bun",
            "run",
            "validate",
            "--dir",
            str(paths.output_dir),
        ],
        cwd=str(frontend_dir),
        env=env,
        check=True,
    )
