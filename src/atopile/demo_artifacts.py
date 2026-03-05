from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from atopile.config import config
from faebryk.exporters.pcb.kicad.artifacts import (
    KicadCliExportError,
    export_glb,
    export_pcb_summary,
    export_step,
    githash_layout,
)

log = logging.getLogger(__name__)


@dataclass
class DemoPaths:
    build_name: str
    build_dir: Path
    output_dir: Path
    step_path: Path
    source_glb_path: Path
    pcb_path: Path
    summary_path: Path
    render_model_path: Path
    mesh_payload_path: Path
    glb_path: Path
    screenshot_dir: Path
    manifest_path: Path
    index_path: Path


def build_demo_bundle(*, output_dir: Path | None = None) -> DemoPaths:
    build_name = config.build.name
    build_dir = config.build.paths.output_base.parent
    demo_dir = output_dir or (build_dir / "demo")
    if demo_dir.exists():
        shutil.rmtree(demo_dir)
    demo_dir.mkdir(parents=True, exist_ok=True)

    _ensure_tool("bun")
    cadquery_python = _resolve_cadquery_python()
    _ensure_layout_derived_artifacts()

    paths = DemoPaths(
        build_name=build_name,
        build_dir=build_dir,
        output_dir=demo_dir,
        step_path=config.build.paths.output_base.with_suffix(".pcba.step"),
        source_glb_path=config.build.paths.output_base.with_suffix(".pcba.glb"),
        pcb_path=config.build.paths.output_base.with_suffix(".kicad_pcb"),
        summary_path=config.build.paths.output_base.with_suffix(".pcb_summary.json"),
        render_model_path=demo_dir / "layout.render-model.json",
        mesh_payload_path=demo_dir / "assembly.mesh.json",
        glb_path=demo_dir / "board.glb",
        screenshot_dir=demo_dir / "screenshots",
        manifest_path=demo_dir / "demo-manifest.json",
        index_path=demo_dir / "index.html",
    )

    _verify_input_artifacts(paths)
    _export_render_model(paths.pcb_path, paths.render_model_path)
    _run_cadquery_tessellation(cadquery_python, paths)
    _build_embed_bundle(paths)
    _optimize_demo_glb(paths)
    _write_manifest(paths)
    _write_index_html(paths)
    _validate_with_puppeteer(paths)
    _write_manifest(paths, poster_path="poster.png")
    return paths


def _ensure_layout_derived_artifacts() -> None:
    layout_path = config.build.paths.layout
    if not layout_path.exists():
        raise RuntimeError(
            "ato demo requires an existing layout file, but none was found at: "
            f"{layout_path}"
        )

    output_base = config.build.paths.output_base
    output_base.parent.mkdir(parents=True, exist_ok=True)

    pcb_path = output_base.with_suffix(".kicad_pcb")
    glb_path = output_base.with_suffix(".pcba.glb")
    step_path = output_base.with_suffix(".pcba.step")
    summary_path = output_base.with_suffix(".pcb_summary.json")

    if not pcb_path.exists():
        shutil.copy2(layout_path, pcb_path)

    missing_exports = [
        not glb_path.exists(),
        not step_path.exists(),
        not summary_path.exists(),
    ]
    if not any(missing_exports):
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_layout = githash_layout(layout_path, Path(tmpdir) / layout_path.name)
        project_dir = layout_path.parent
        if not glb_path.exists():
            try:
                export_glb(tmp_layout, glb_file=glb_path, project_dir=project_dir)
            except KicadCliExportError as exc:
                raise RuntimeError(f"Failed to generate demo GLB: {exc}") from exc
        if not step_path.exists():
            try:
                export_step(tmp_layout, step_file=step_path, project_dir=project_dir)
            except KicadCliExportError as exc:
                raise RuntimeError(f"Failed to generate demo STEP: {exc}") from exc
        if not summary_path.exists():
            try:
                export_pcb_summary(tmp_layout, summary_file=summary_path)
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to generate demo PCB summary: {exc}"
                ) from exc


def _ensure_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required tool not found on PATH: {name}")
    return path


def _resolve_cadquery_python() -> str:
    candidates = [
        os.environ.get("ATO_DEMO_CADQUERY_PYTHON"),
        sys.executable,
    ]
    checked: list[str] = []
    for candidate in candidates:
        if not candidate:
            continue
        checked.append(candidate)
        result = subprocess.run(
            [
                candidate,
                "-c",
                "import cadquery, OCP; print(cadquery.__version__)",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return candidate
    raise RuntimeError(
        "CadQuery with OCP is not available. Set ATO_DEMO_CADQUERY_PYTHON to an "
        "interpreter where `import cadquery, OCP` succeeds. Checked: "
        + ", ".join(checked)
    )


def _verify_input_artifacts(paths: DemoPaths) -> None:
    required = [
        paths.step_path,
        paths.source_glb_path,
        paths.pcb_path,
        paths.summary_path,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(
            "ato demo could not find required build artifacts:\n" + "\n".join(missing)
        )


def _export_render_model(pcb_path: Path, output_path: Path) -> None:
    from atopile.layout_server.pcb_manager import PcbManager

    mgr = PcbManager()
    mgr.load(pcb_path)
    model = mgr.get_render_model()
    output_path.write_text(model.model_dump_json(), encoding="utf-8")


def _run_cadquery_tessellation(cadquery_python: str, paths: DemoPaths) -> None:
    script_path = Path(__file__).with_name("demo_cadquery.py")
    cmd = [
        cadquery_python,
        str(script_path),
        "--step",
        str(paths.step_path),
        "--summary",
        str(paths.summary_path),
        "--output",
        str(paths.mesh_payload_path),
    ]
    log.info("Running CadQuery tessellation: %s", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _build_embed_bundle(paths: DemoPaths) -> None:
    bundle_dir = Path(__file__).parent / "demo_frontend"
    _ensure_bun_install(bundle_dir)
    env = os.environ.copy()
    env["ATO_DEMO_OUT_DIR"] = str(paths.output_dir)
    subprocess.run(
        ["bun", "run", "build"],
        cwd=str(bundle_dir),
        env=env,
        check=True,
    )
    dist_dir = bundle_dir / "dist"
    shutil.copy2(dist_dir / "embed.js", paths.output_dir / "embed.js")


def _optimize_demo_glb(paths: DemoPaths) -> None:
    bundle_dir = Path(__file__).parent / "demo_frontend"
    subprocess.run(
        [
            "bun",
            "x",
            "@gltf-transform/cli",
            "optimize",
            str(paths.source_glb_path),
            str(paths.glb_path),
            "--compress",
            "meshopt",
            "--texture-compress",
            "false",
        ],
        cwd=str(bundle_dir),
        check=True,
    )


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


def _validate_with_puppeteer(paths: DemoPaths) -> None:
    bundle_dir = Path(__file__).parent / "demo_frontend"
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
        cwd=str(bundle_dir),
        env=env,
        check=True,
    )
