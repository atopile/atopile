from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ruff: noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path = [
    entry for entry in sys.path if entry and Path(entry).resolve() != SCRIPT_DIR
]

import cadquery as cq


def _build_board_thickness(summary: dict) -> float:
    stackup = summary.get("stackup") or {}
    thickness = stackup.get("total_thickness_mm")
    if isinstance(thickness, (int, float)) and thickness > 0:
        return float(thickness)
    return 1.6


def main() -> None:
    parser = argparse.ArgumentParser(description="Tessellate STEP with CadQuery")
    parser.add_argument("--step", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--tolerance", type=float, default=0.12)
    parser.add_argument("--angular-tolerance", type=float, default=0.2)
    args = parser.parse_args()

    step_path = Path(args.step)
    summary_path = Path(args.summary)
    output_path = Path(args.output)

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    board_thickness = _build_board_thickness(summary)

    workplane = cq.importers.importStep(str(step_path))
    shape = workplane.val()
    vertices, triangles = shape.tessellate(args.tolerance, args.angular_tolerance)

    bbox = shape.BoundingBox()
    payload = {
        "mesh": {
            "positions": [[float(v.x), float(v.y), float(v.z)] for v in vertices],
            "triangles": [[int(a), int(b), int(c)] for a, b, c in triangles],
        },
        "boardThicknessMm": board_thickness,
        "bounds": {
            "xmin": float(bbox.xmin),
            "ymin": float(bbox.ymin),
            "zmin": float(bbox.zmin),
            "xmax": float(bbox.xmax),
            "ymax": float(bbox.ymax),
            "zmax": float(bbox.zmax),
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    main()
