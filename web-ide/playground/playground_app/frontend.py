from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from playground_app.types_codegen import generate_types


def _playground_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _web_root() -> Path:
    return _playground_root() / "web"


def _bundle_paths() -> list[Path]:
    static_dir = _playground_root() / "playground_app" / "static"
    return [
        static_dir / "landing.js",
        static_dir / "dashboard.js",
    ]


def _generated_types_path() -> Path:
    return _web_root() / "src" / "generated" / "api-types.ts"


def _source_paths() -> list[Path]:
    root = _web_root() / "src"
    return list(root.rglob("*.ts"))


def _is_stale(target: Path, sources: list[Path]) -> bool:
    if not target.exists():
        return True
    target_mtime = target.stat().st_mtime
    return any(path.stat().st_mtime > target_mtime for path in sources if path.exists())


def build_frontend(force: bool = False) -> None:
    bun = shutil.which("bun")
    if not bun:
        raise RuntimeError("bun is required to build landing assets")

    generate_types(_generated_types_path())

    bundles = _bundle_paths()
    sources = _source_paths() + [_generated_types_path()]
    if not force and all(not _is_stale(bundle, sources) for bundle in bundles):
        return

    web_root = _web_root()
    subprocess.run([bun, "install"], cwd=web_root, check=True)
    subprocess.run([bun, "run", "build"], cwd=web_root, check=True)
