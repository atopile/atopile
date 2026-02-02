#!/usr/bin/env python3
"""
STEP Model to KiCad Footprint Alignment Tool

This tool analyzes STEP 3D models and KiCad footprints to compute
alignment offsets for proper 3D visualization in KiCad.

Usage:
    python step_alignment_tool.py <step_file> <footprint_file>
    python step_alignment_tool.py --test  # Run on test data
"""

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Add the src directory to path for imports
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from faebryk.libs.kicad.fileformats import kicad


@dataclass
class Point3D:
    x: float
    y: float
    z: float


@dataclass
class BoundingBox:
    min: Point3D
    max: Point3D

    @property
    def size(self) -> Point3D:
        return Point3D(
            self.max.x - self.min.x,
            self.max.y - self.min.y,
            self.max.z - self.min.z,
        )

    @property
    def center(self) -> Point3D:
        return Point3D(
            (self.min.x + self.max.x) / 2,
            (self.min.y + self.max.y) / 2,
            (self.min.z + self.max.z) / 2,
        )


@dataclass
class Pin:
    """Cylindrical pin"""

    x: float
    y: float
    radius: float


@dataclass
class RectangularPin:
    """Rectangular pin (for headers, etc)"""

    x: float
    y: float
    z: float
    size_x: float
    size_y: float
    min_z: float
    max_z: float
    is_vertical: bool


@dataclass
class Point2D:
    x: float
    y: float


@dataclass
class Edge3D:
    """3D edge segment"""

    start: Point3D
    end: Point3D


@dataclass
class HorizontalPlane:
    """Horizontal plane at a specific Z level"""

    z: float
    count: int  # Number of faces at this Z level


@dataclass
class Circle3D:
    """Circle in 3D space"""

    x: float
    y: float
    z: float
    radius: float
    normal: Point3D  # Normal direction


@dataclass
class StepAnalysis:
    """Results from analyzing a STEP file"""

    file: str
    entities: int
    bounding_box: Optional[BoundingBox]
    size: Optional[Point3D]
    bottom_face_z: Optional[float]
    centroid: Optional[Point3D]
    vertical_pins: list[Pin]
    rectangular_pins: list[RectangularPin]
    vertices: list[Point3D]
    silhouette_xy: list[Point2D]  # Top-down outline
    silhouette_xz: list[Point2D]  # Side outline
    edges: list[Edge3D]  # Actual geometry edges for visualization
    horizontal_planes: list[HorizontalPlane]  # Z levels for alignment
    circles: list[Circle3D]  # Circle geometry

    @classmethod
    def from_json(cls, data: dict) -> "StepAnalysis":
        bbox = None
        if data.get("bounding_box"):
            bbox = BoundingBox(
                min=Point3D(*data["bounding_box"]["min"]),
                max=Point3D(*data["bounding_box"]["max"]),
            )

        size = None
        if data.get("size"):
            size = Point3D(*data["size"])

        centroid = None
        if data.get("centroid"):
            centroid = Point3D(*data["centroid"])

        pins = [Pin(p["x"], p["y"], p["radius"]) for p in data.get("vertical_pins", [])]

        # Parse rectangular pins
        rect_pins = [
            RectangularPin(
                x=p["x"],
                y=p["y"],
                z=p["z"],
                size_x=p["size_x"],
                size_y=p["size_y"],
                min_z=p["min_z"],
                max_z=p["max_z"],
                is_vertical=p["vertical"],
            )
            for p in data.get("rectangular_pins", [])
        ]

        # Parse vertices (list of [x, y, z] arrays)
        vertices = [Point3D(*v) for v in data.get("vertices", [])]

        # Parse silhouettes
        silhouette_xy = [Point2D(p[0], p[1]) for p in data.get("silhouette_xy", [])]
        silhouette_xz = [Point2D(p[0], p[1]) for p in data.get("silhouette_xz", [])]

        # Parse edges (new detailed geometry)
        edges = [
            Edge3D(
                start=Point3D(e["start"][0], e["start"][1], e["start"][2]),
                end=Point3D(e["end"][0], e["end"][1], e["end"][2]),
            )
            for e in data.get("edges", [])
        ]

        # Parse horizontal planes (for Z-alignment)
        horizontal_planes = [
            HorizontalPlane(z=hp["z"], count=hp["count"])
            for hp in data.get("horizontal_planes", [])
        ]

        # Parse circles
        circles = [
            Circle3D(
                x=c["x"],
                y=c["y"],
                z=c["z"],
                radius=c["radius"],
                normal=Point3D(c["normal"][0], c["normal"][1], c["normal"][2]),
            )
            for c in data.get("circles", [])
        ]

        return cls(
            file=data.get("file", ""),
            entities=data.get("entities", 0),
            bounding_box=bbox,
            size=size,
            bottom_face_z=data.get("bottom_face_z"),
            centroid=centroid,
            vertical_pins=pins,
            rectangular_pins=rect_pins,
            vertices=vertices,
            silhouette_xy=silhouette_xy,
            silhouette_xz=silhouette_xz,
            edges=edges,
            horizontal_planes=horizontal_planes,
            circles=circles,
        )


@dataclass
class FootprintPad:
    """Pad from a KiCad footprint"""

    name: str
    x: float
    y: float
    width: float
    height: float
    rotation: float
    is_through_hole: bool
    drill_size: Optional[float] = None


@dataclass
class FootprintAnalysis:
    """Results from analyzing a KiCad footprint"""

    name: str
    pads: list[FootprintPad]

    @property
    def centroid(self) -> Point3D:
        if not self.pads:
            return Point3D(0, 0, 0)
        x = sum(p.x for p in self.pads) / len(self.pads)
        y = sum(p.y for p in self.pads) / len(self.pads)
        return Point3D(x, y, 0)

    @property
    def through_hole_pads(self) -> list[FootprintPad]:
        return [p for p in self.pads if p.is_through_hole]

    @property
    def smd_pads(self) -> list[FootprintPad]:
        return [p for p in self.pads if not p.is_through_hole]


@dataclass
class AlignmentResult:
    """Computed alignment offsets"""

    offset_x: float
    offset_y: float
    offset_z: float
    rotation: float  # degrees
    confidence: float  # 0-1, how confident we are in this alignment
    method: str  # description of alignment method used


def analyze_step_file(step_path: Path) -> Optional[StepAnalysis]:
    """
    Analyze a STEP file using the Zig parser.

    This compiles and runs the analyze.zig program which outputs JSON analysis.
    In the future, this should use proper Python bindings.
    """
    zig_dir = ROOT / "src" / "faebryk" / "core" / "zig"
    step_dir = zig_dir / "src" / "step"
    analyze_src = step_dir / "analyze.zig"
    analyze_exe = zig_dir / "analyze"

    # Check if analyze.zig exists
    if not analyze_src.exists():
        print(f"analyze.zig not found at {analyze_src}")
        return None

    try:
        # Compile analyze.zig if needed (check if exe exists and is newer than source)
        needs_compile = not analyze_exe.exists()
        if not needs_compile:
            src_mtime = analyze_src.stat().st_mtime
            exe_mtime = analyze_exe.stat().st_mtime
            needs_compile = src_mtime > exe_mtime

        if needs_compile:
            print("  Compiling STEP analyzer...")
            result = subprocess.run(
                [
                    "zig",
                    "build-exe",
                    str(analyze_src),
                    f"-femit-bin={analyze_exe}",
                    "-freference-trace",
                ],
                cwd=step_dir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                print(f"Zig compilation failed: {result.stderr}")
                return None

        # Run the analyzer
        result = subprocess.run(
            [str(analyze_exe), str(step_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            print(f"Analysis failed: {result.stderr}")
            return None

        # Parse JSON output
        data = json.loads(result.stdout)
        if "error" in data:
            print(f"Analysis error: {data['error']}")
            return None

        return StepAnalysis.from_json(data)

    except subprocess.TimeoutExpired:
        print("Analysis timed out")
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse output: {e}")
        print(f"Raw output: {result.stdout[:500] if result.stdout else 'empty'}")
        return None


def analyze_footprint(fp_path: Path) -> FootprintAnalysis:
    """Analyze a KiCad footprint file"""
    fp_file = kicad.loads(kicad.footprint.FootprintFile, fp_path)
    fp = fp_file.footprint

    pads = []
    for pad in fp.pads:
        # Only include pads on copper layers
        if not any("Cu" in layer for layer in pad.layers):
            continue

        is_th = pad.type in ("thru_hole", "np_thru_hole")
        drill_size = None
        if pad.drill:
            drill_size = pad.drill.size_x or (
                pad.drill.size_y if hasattr(pad.drill, "size_y") else None
            )

        pads.append(
            FootprintPad(
                name=pad.name,
                x=pad.at.x,
                y=pad.at.y,
                width=pad.size.w,
                height=pad.size.h or pad.size.w,
                rotation=pad.at.r or 0,
                is_through_hole=is_th,
                drill_size=drill_size,
            )
        )

    return FootprintAnalysis(name=fp.name, pads=pads)


def _match_pins_to_holes(
    pins: list[Pin], holes: list[FootprintPad], max_distance: float = 2.0
) -> list[tuple[Pin, FootprintPad, float]]:
    """
    Match STEP cylindrical pins to footprint holes using nearest-neighbor with radius validation.

    Returns list of (pin, hole, distance) tuples for matched pairs.
    Only matches if pin radius is compatible with hole drill size.
    """
    import math

    matches = []
    used_holes = set()

    for pin in pins:
        best_hole = None
        best_dist = float("inf")

        for i, hole in enumerate(holes):
            if i in used_holes:
                continue

            # Check radius compatibility (pin should fit in hole)
            if hole.drill_size:
                hole_radius = hole.drill_size / 2
                # Pin radius should be smaller than or close to hole radius
                if pin.radius > hole_radius * 1.5:
                    continue

            # Compute distance
            dist = math.sqrt((pin.x - hole.x) ** 2 + (pin.y - hole.y) ** 2)

            if dist < best_dist and dist < max_distance:
                best_dist = dist
                best_hole = (i, hole)

        if best_hole:
            used_holes.add(best_hole[0])
            matches.append((pin, best_hole[1], best_dist))

    return matches


def _match_rect_pins_to_holes(
    rect_pins: list[RectangularPin], holes: list[FootprintPad], max_distance: float = 2.0
) -> list[tuple[RectangularPin, FootprintPad, float]]:
    """
    Match STEP rectangular pins to footprint holes.

    Returns list of (rect_pin, hole, distance) tuples for matched pairs.
    """
    import math

    matches = []
    used_holes = set()

    for pin in rect_pins:
        best_hole = None
        best_dist = float("inf")

        for i, hole in enumerate(holes):
            if i in used_holes:
                continue

            # Check size compatibility - pin should fit in hole
            if hole.drill_size:
                # Rectangular pin diagonal should be smaller than hole diameter
                pin_diagonal = math.sqrt(pin.size_x**2 + pin.size_y**2)
                if pin_diagonal > hole.drill_size * 1.2:
                    continue

            # Compute distance
            dist = math.sqrt((pin.x - hole.x) ** 2 + (pin.y - hole.y) ** 2)

            if dist < best_dist and dist < max_distance:
                best_dist = dist
                best_hole = (i, hole)

        if best_hole:
            used_holes.add(best_hole[0])
            matches.append((pin, best_hole[1], best_dist))

    return matches


def _footprint_driven_alignment(
    step: "StepAnalysis", footprint: "FootprintAnalysis"
) -> Optional[AlignmentResult]:
    """
    Footprint-driven alignment: Use pad positions to find matching STEP features.

    Instead of detecting all features then matching, we:
    1. Know the expected pad pattern from footprint
    2. Search STEP geometry for features near each expected position
    3. Compute optimal offset from aggregate matches
    """
    import math
    from itertools import combinations

    pads = footprint.through_hole_pads if footprint.through_hole_pads else footprint.smd_pads
    if len(pads) < 2:
        return None

    # Get all detectable features from STEP
    all_features = []

    # Cylindrical pins
    for pin in step.vertical_pins:
        all_features.append({
            'x': pin.x, 'y': pin.y,
            'type': 'cylinder',
            'size': pin.radius * 2
        })

    # Rectangular pins
    for pin in step.rectangular_pins:
        all_features.append({
            'x': pin.x, 'y': pin.y,
            'type': 'rectangle',
            'size': max(pin.size_x, pin.size_y)
        })

    if len(all_features) < 2:
        return None

    # Calculate pad arrangement (spacing pattern)
    pad_positions = [(p.x, p.y) for p in pads]
    feature_positions = [(f['x'], f['y']) for f in all_features]

    # Try to find the best offset by matching patterns
    # Use RANSAC-like approach: try different feature-to-pad correspondences
    best_result = None
    best_inlier_count = 0

    # Try matching first pad to each feature
    for i, feature in enumerate(all_features):
        # Hypothesize this feature corresponds to first pad
        offset_x = pad_positions[0][0] - feature_positions[i][0]
        offset_y = pad_positions[0][1] - feature_positions[i][1]

        # Count how many other pads have a feature nearby with this offset
        inliers = 0
        inlier_offsets = []

        for pad_x, pad_y in pad_positions:
            # Expected feature position
            expected_fx = pad_x - offset_x
            expected_fy = pad_y - offset_y

            # Find closest feature to expected position
            min_dist = float('inf')
            closest_feature = None
            for fx, fy in feature_positions:
                dist = math.sqrt((fx - expected_fx)**2 + (fy - expected_fy)**2)
                if dist < min_dist:
                    min_dist = dist
                    closest_feature = (fx, fy)

            # If close enough, it's an inlier
            tolerance = 1.0  # 1mm tolerance
            if min_dist < tolerance and closest_feature:
                inliers += 1
                # Refined offset from this match
                inlier_offsets.append((
                    pad_x - closest_feature[0],
                    pad_y - closest_feature[1]
                ))

        if inliers > best_inlier_count:
            best_inlier_count = inliers
            if inlier_offsets:
                # Use median offset
                ox_list = sorted([o[0] for o in inlier_offsets])
                oy_list = sorted([o[1] for o in inlier_offsets])
                mid = len(ox_list) // 2

                # Compute consistency
                mean_ox = sum(ox_list) / len(ox_list)
                mean_oy = sum(oy_list) / len(oy_list)
                variance = sum((ox - mean_ox)**2 + (oy - mean_oy)**2 for ox, oy in inlier_offsets) / len(inlier_offsets)
                alignment_error = math.sqrt(variance)

                match_ratio = inliers / len(pads)

                if alignment_error < 0.1:
                    confidence = min(0.95, 0.6 + 0.35 * match_ratio)
                elif alignment_error < 0.5:
                    confidence = min(0.85, 0.4 + 0.45 * match_ratio)
                else:
                    confidence = 0.3 + 0.4 * match_ratio

                best_result = AlignmentResult(
                    offset_x=ox_list[mid],
                    offset_y=oy_list[mid],
                    offset_z=0,  # Will be set later
                    rotation=0,
                    confidence=confidence,
                    method=f"pattern_match ({inliers}/{len(pads)} pads)"
                )

    return best_result


def check_collision(
    step: "StepAnalysis",
    footprint: "FootprintAnalysis",
    offset_x: float,
    offset_y: float,
    offset_z: float,
) -> tuple[bool, list[str]]:
    """
    Check for collisions between STEP model and footprint.

    Returns (has_collision, list of collision descriptions).

    A good alignment should have:
    - Pins passing through holes (not colliding with copper)
    - Model bottom at or above Z=0
    - No model geometry intersecting the board plane
    """
    import math

    collisions = []

    # Check 1: Model bottom should be at or above board surface
    if step.bottom_face_z is not None:
        effective_bottom = step.bottom_face_z + offset_z
        if effective_bottom < -0.1:  # Allow small tolerance
            collisions.append(f"Model bottom at Z={effective_bottom:.2f}mm (below board)")

    # Check 2: Through-hole pins should align with holes
    # For each TH pad, check if there's a pin nearby
    for pad in footprint.through_hole_pads:
        pin_found = False

        # Check cylindrical pins
        for pin in step.vertical_pins:
            px, py = pin.x + offset_x, pin.y + offset_y
            dist = math.sqrt((px - pad.x) ** 2 + (py - pad.y) ** 2)
            if dist < (pad.drill_size / 2 if pad.drill_size else 0.5):
                pin_found = True
                break

        # Check rectangular pins
        if not pin_found:
            for pin in step.rectangular_pins:
                px, py = pin.x + offset_x, pin.y + offset_y
                dist = math.sqrt((px - pad.x) ** 2 + (py - pad.y) ** 2)
                if dist < (pad.drill_size / 2 if pad.drill_size else 0.5) + 0.3:
                    pin_found = True
                    break

        if not pin_found and pad.drill_size:
            # Check if model geometry passes through the hole area
            # using vertices
            hole_occupied = False
            for v in step.vertices:
                vx, vy, vz = v.x + offset_x, v.y + offset_y, v.z + offset_z
                dist_xy = math.sqrt((vx - pad.x) ** 2 + (vy - pad.y) ** 2)
                # If vertex is in hole area and below board
                if dist_xy < pad.drill_size / 2 and vz < 0:
                    hole_occupied = True
                    break

            if not hole_occupied:
                collisions.append(f"No pin found for hole at ({pad.x:.2f}, {pad.y:.2f})")

    # Check 3: For SMD pads, model shouldn't have geometry at pad level
    # (pins shouldn't collide with SMD pads)
    for pad in footprint.smd_pads:
        for pin in step.vertical_pins:
            px, py = pin.x + offset_x, pin.y + offset_y
            # Check if cylindrical pin overlaps with SMD pad
            if (
                abs(px - pad.x) < (pad.width / 2 + pin.radius)
                and abs(py - pad.y) < (pad.height / 2 + pin.radius)
            ):
                collisions.append(
                    f"Pin at ({px:.2f}, {py:.2f}) collides with SMD pad at ({pad.x:.2f}, {pad.y:.2f})"
                )

    has_collision = len(collisions) > 0
    return has_collision, collisions


def find_optimal_z_offset(
    step: StepAnalysis, footprint: FootprintAnalysis, xy_offset: tuple[float, float]
) -> tuple[float, float]:
    """
    Find the optimal Z offset for through-hole components using horizontal planes.

    Strategy:
    1. Get all horizontal plane Z levels from the STEP model
    2. For each candidate Z level (sorted from lowest to highest):
       - Check if pins extend below board level (Z < 0)
       - Check if body doesn't collide with board (body bottom at Z >= 0)
    3. Return the Z offset that satisfies both conditions

    Returns: (z_offset, confidence)
    """
    if not step.horizontal_planes:
        # No horizontal planes detected, fall back to bottom_face_z
        if step.bottom_face_z is not None:
            return -step.bottom_face_z, 0.5
        if step.bounding_box:
            return -step.bounding_box.min.z, 0.3
        return 0.0, 0.1

    th_pads = footprint.through_hole_pads
    if not th_pads:
        # SMD component - just use bottom_face_z
        if step.bottom_face_z is not None:
            return -step.bottom_face_z, 0.8
        return 0.0, 0.3

    ox, oy = xy_offset

    # Get all horizontal plane Z levels, sorted from lowest to highest
    z_levels = sorted([hp.z for hp in step.horizontal_planes])

    # For through-hole: we want:
    # - Pins to extend below Z=0 (into the board)
    # - Body bottom to be at or above Z=0

    # Find pin Z ranges
    cyl_pin_z_min = None
    rect_pin_z_min = None

    if step.vertical_pins:
        # Cylindrical pins don't have explicit Z range, estimate from bottom_face_z
        cyl_pin_z_min = step.bottom_face_z if step.bottom_face_z is not None else 0

    if step.rectangular_pins:
        rect_pin_z_min = min(p.min_z for p in step.rectangular_pins)

    # Combine to get overall pin bottom
    pin_z_min = None
    if cyl_pin_z_min is not None and rect_pin_z_min is not None:
        pin_z_min = min(cyl_pin_z_min, rect_pin_z_min)
    elif cyl_pin_z_min is not None:
        pin_z_min = cyl_pin_z_min
    elif rect_pin_z_min is not None:
        pin_z_min = rect_pin_z_min

    if pin_z_min is None:
        # No pins detected, use bottom_face_z
        if step.bottom_face_z is not None:
            return -step.bottom_face_z, 0.4
        return 0.0, 0.2

    # Find horizontal planes that could be the "board contact" surface
    # These should be above the pin bottoms
    candidate_surfaces = [z for z in z_levels if z > pin_z_min + 0.5]

    if not candidate_surfaces:
        # No good candidate surfaces, use the most common approach
        if step.bottom_face_z is not None:
            return -step.bottom_face_z, 0.5
        return -pin_z_min, 0.4

    # The first candidate (lowest above pins) is likely the board contact surface
    board_contact_z = candidate_surfaces[0]

    # Also check for planes with high face counts (more likely to be actual surfaces)
    plane_counts = {hp.z: hp.count for hp in step.horizontal_planes}
    high_count_candidates = [
        z for z in candidate_surfaces if plane_counts.get(z, 0) >= 3
    ]

    if high_count_candidates:
        # Prefer planes with more faces (likely major surfaces)
        board_contact_z = high_count_candidates[0]

    # Z offset to place board_contact_z at Z=0
    z_offset = -board_contact_z

    # Verify pins extend below Z=0 with this offset
    pin_bottom_after = pin_z_min + z_offset
    if pin_bottom_after > -0.5:  # Pins should go at least 0.5mm into board
        # Adjust to ensure pins go through
        z_offset = -pin_z_min - 1.0  # Put pins 1mm below board

    confidence = 0.7 if len(high_count_candidates) > 0 else 0.5
    return z_offset, confidence


def compute_alignment(
    step: StepAnalysis, footprint: FootprintAnalysis
) -> AlignmentResult:
    """
    Compute alignment offsets between STEP model and footprint.

    Alignment strategies (in priority order):
    1. Footprint-driven pattern matching: Use pad positions to find STEP features
    2. Through-hole pin matching: Match individual STEP pins to footprint holes
    3. SMD centroid: Align bounding box center to pad centroid
    4. Fallback: Use bounding box center
    """
    import math

    # Default result
    result = AlignmentResult(
        offset_x=0, offset_y=0, offset_z=0, rotation=0, confidence=0, method="none"
    )

    if not step.bounding_box:
        return result

    # Strategy 0: Footprint-driven pattern matching (best approach)
    # This uses the pad positions to search for matching features in STEP
    pattern_result = _footprint_driven_alignment(step, footprint)
    if pattern_result and pattern_result.confidence >= 0.5:
        # Set Z offset using smart alignment for through-hole parts
        if footprint.through_hole_pads:
            # For through-hole: pins must go THROUGH the board
            z_offset, z_conf = find_optimal_z_offset(
                step, footprint, (pattern_result.offset_x, pattern_result.offset_y)
            )
            pattern_result.offset_z = z_offset
            # Blend confidence
            pattern_result.confidence = (pattern_result.confidence + z_conf) / 2
        else:
            # For SMD: bottom of model at board surface
            if step.bottom_face_z is not None:
                pattern_result.offset_z = -step.bottom_face_z
            else:
                pattern_result.offset_z = -step.bounding_box.min.z
        return pattern_result

    th_pads = footprint.through_hole_pads
    step_cyl_pins = step.vertical_pins
    step_rect_pins = step.rectangular_pins

    # Combine all detected pins for counting
    total_step_pins = len(step_cyl_pins) + len(step_rect_pins)

    # Strategy 1: Through-hole alignment via individual pin matching
    # Try both cylindrical and rectangular pins
    if len(th_pads) >= 2 and total_step_pins >= 2:
        # Compute footprint centroid
        fp_cx = sum(p.x for p in th_pads) / len(th_pads)
        fp_cy = sum(p.y for p in th_pads) / len(th_pads)

        # Compute pin centroid (combine cylindrical and rectangular)
        all_pin_x = [p.x for p in step_cyl_pins] + [p.x for p in step_rect_pins]
        all_pin_y = [p.y for p in step_cyl_pins] + [p.y for p in step_rect_pins]
        pin_cx = sum(all_pin_x) / len(all_pin_x)
        pin_cy = sum(all_pin_y) / len(all_pin_y)

        initial_ox = fp_cx - pin_cx
        initial_oy = fp_cy - pin_cy

        # Try matching cylindrical pins first
        offset_cyl_pins = [
            Pin(x=p.x + initial_ox, y=p.y + initial_oy, radius=p.radius)
            for p in step_cyl_pins
        ]
        cyl_matches = _match_pins_to_holes(offset_cyl_pins, th_pads) if step_cyl_pins else []

        # Then try rectangular pins
        offset_rect_pins = [
            RectangularPin(
                x=p.x + initial_ox,
                y=p.y + initial_oy,
                z=p.z,
                size_x=p.size_x,
                size_y=p.size_y,
                min_z=p.min_z,
                max_z=p.max_z,
                is_vertical=p.is_vertical,
            )
            for p in step_rect_pins
        ]
        rect_matches = _match_rect_pins_to_holes(offset_rect_pins, th_pads) if step_rect_pins else []

        # Combine all matches
        all_matches_offsets = []

        for pin, hole, _dist in cyl_matches:
            orig_pin_x = pin.x - initial_ox
            orig_pin_y = pin.y - initial_oy
            all_matches_offsets.append((hole.x - orig_pin_x, hole.y - orig_pin_y))

        for pin, hole, _dist in rect_matches:
            orig_pin_x = pin.x - initial_ox
            orig_pin_y = pin.y - initial_oy
            all_matches_offsets.append((hole.x - orig_pin_x, hole.y - orig_pin_y))

        total_matches = len(cyl_matches) + len(rect_matches)

        if total_matches >= 2:
            # Compute refined offset from matched pairs
            offsets_x = [o[0] for o in all_matches_offsets]
            offsets_y = [o[1] for o in all_matches_offsets]

            # Use median for robustness against outliers
            offsets_x.sort()
            offsets_y.sort()
            mid = len(offsets_x) // 2
            result.offset_x = offsets_x[mid]
            result.offset_y = offsets_y[mid]

            # Compute match quality
            match_ratio = total_matches / min(total_step_pins, len(th_pads))

            # Compute alignment error (std dev of offsets)
            mean_ox = sum(offsets_x) / len(offsets_x)
            mean_oy = sum(offsets_y) / len(offsets_y)
            variance = sum(
                (ox - mean_ox) ** 2 + (oy - mean_oy) ** 2
                for ox, oy in zip(offsets_x, offsets_y)
            ) / len(offsets_x)
            alignment_error = math.sqrt(variance)

            # High confidence if many matches with low error
            if alignment_error < 0.1:  # Sub-0.1mm consistency
                result.confidence = min(0.95, 0.7 + 0.25 * match_ratio)
            elif alignment_error < 0.5:
                result.confidence = min(0.85, 0.5 + 0.35 * match_ratio)
            else:
                result.confidence = 0.4 + 0.3 * match_ratio

            pin_type = "cyl" if len(cyl_matches) > len(rect_matches) else "rect"
            result.method = f"pin_matching ({total_matches}/{total_step_pins} {pin_type})"

        else:
            # Fall back to centroid if matching failed
            result.offset_x = initial_ox
            result.offset_y = initial_oy
            result.method = "through_hole_centroid"
            result.confidence = 0.5

        # Z offset: use smart horizontal plane-based alignment for through-hole
        z_offset, z_confidence = find_optimal_z_offset(
            step, footprint, (result.offset_x, result.offset_y)
        )
        result.offset_z = z_offset
        # Blend Z confidence with XY confidence
        result.confidence = (result.confidence + z_confidence) / 2

    # Strategy 2: SMD alignment via bounding box center
    elif len(footprint.smd_pads) >= 2:
        fp_centroid = footprint.centroid
        step_center = step.bounding_box.center

        result.offset_x = fp_centroid.x - step_center.x
        result.offset_y = fp_centroid.y - step_center.y

        # Z offset: bottom of model should sit on board surface
        if step.bottom_face_z is not None:
            result.offset_z = -step.bottom_face_z
        else:
            result.offset_z = -step.bounding_box.min.z

        result.method = "smd_centroid"
        result.confidence = 0.6

    # Strategy 3: Fallback - pure bounding box
    else:
        fp_centroid = footprint.centroid
        step_center = step.bounding_box.center

        result.offset_x = fp_centroid.x - step_center.x
        result.offset_y = fp_centroid.y - step_center.y
        result.offset_z = -step.bounding_box.min.z

        result.method = "bbox_fallback"
        result.confidence = 0.3

    return result


def visualize_alignment(
    step: StepAnalysis,
    footprint: FootprintAnalysis,
    alignment: AlignmentResult,
    output_path: Optional[Path] = None,
):
    """
    Create visualization of the alignment including 3D isometric view.

    Shows:
    - Top view: Footprint pads and STEP bounding box (X/Y)
    - Side view: Z alignment showing model height relative to board surface
    - 3D view: Isometric view of aligned model and footprint
    """
    try:
        import matplotlib.patches as mpatches
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    except ImportError:
        print("matplotlib not installed, skipping visualization")
        return

    # Create figure with 2x3 grid
    fig = plt.figure(figsize=(18, 10))

    # Top row: 2D views
    ax1 = fig.add_subplot(2, 3, 1)  # Top view before
    ax2 = fig.add_subplot(2, 3, 2)  # Top view after
    ax3 = fig.add_subplot(2, 3, 3, projection="3d")  # 3D isometric

    # Bottom row: Side views
    ax4 = fig.add_subplot(2, 3, 4)  # Side view before
    ax5 = fig.add_subplot(2, 3, 5)  # Side view after
    ax6 = fig.add_subplot(2, 3, 6, projection="3d")  # 3D aligned

    # Top-left: X/Y Before alignment
    ax1.set_title("Top View - Before")
    _plot_footprint_and_step_xy(ax1, step, footprint, 0, 0)
    ax1.set_aspect("equal")
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=0, color="k", linewidth=0.5)
    ax1.axvline(x=0, color="k", linewidth=0.5)
    ax1.set_xlabel("X (mm)")
    ax1.set_ylabel("Y (mm)")

    # Top-middle: X/Y After alignment
    ax2.set_title(f"Top View - After ({alignment.method})")
    _plot_footprint_and_step_xy(ax2, step, footprint, alignment.offset_x, alignment.offset_y)
    ax2.set_aspect("equal")
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0, color="k", linewidth=0.5)
    ax2.axvline(x=0, color="k", linewidth=0.5)
    ax2.set_xlabel("X (mm)")
    ax2.set_ylabel("Y (mm)")

    # Top-right: 3D Before alignment
    ax3.set_title("3D View - Before")
    _plot_3d_view(ax3, step, footprint, 0, 0, 0)

    # Bottom-left: X/Z Side view Before alignment
    ax4.set_title("Side View (X-Z) - Before")
    _plot_side_view_xz(ax4, step, footprint, 0, 0)
    ax4.grid(True, alpha=0.3)
    ax4.axhline(y=0, color="k", linewidth=1.5)
    ax4.set_xlabel("X (mm)")
    ax4.set_ylabel("Z (mm)")

    # Bottom-middle: X/Z Side view After alignment
    ax5.set_title(f"Side View - After (Z: {alignment.offset_z:.2f}mm)")
    _plot_side_view_xz(ax5, step, footprint, alignment.offset_x, alignment.offset_z)
    ax5.grid(True, alpha=0.3)
    ax5.axhline(y=0, color="k", linewidth=1.5)
    ax5.set_xlabel("X (mm)")
    ax5.set_ylabel("Z (mm)")

    # Bottom-right: 3D After alignment
    ax6.set_title(f"3D View - After (conf={alignment.confidence:.2f})")
    _plot_3d_view(
        ax6, step, footprint, alignment.offset_x, alignment.offset_y, alignment.offset_z
    )

    # Add overall title with warnings if needed
    title = f"Alignment: {step.file}"
    if alignment.confidence < 0.5:
        title += " [LOW CONFIDENCE]"
    elif "centroid" in alignment.method and step.vertical_pins:
        title += " [Pin matching failed]"

    # Show pin counts
    n_cyl = len(step.vertical_pins)
    n_rect = len(step.rectangular_pins)
    title += f" | Pins: {n_cyl} cyl, {n_rect} rect"

    fig.suptitle(title, fontsize=12, fontweight="bold")

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150)
        print(f"Saved visualization to {output_path}")
    else:
        plt.show()


def _plot_3d_view(ax, step, footprint, ox, oy, oz):
    """Helper to plot 3D isometric view with detailed wireframe geometry"""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import numpy as np

    # Plot STEP edges as wireframe (much more detailed than vertices)
    if step.edges:
        # Limit edges if there are too many for performance
        max_edges = 2000
        edges_to_plot = step.edges[:max_edges] if len(step.edges) > max_edges else step.edges
        for edge in edges_to_plot:
            ax.plot(
                [edge.start.x + ox, edge.end.x + ox],
                [edge.start.y + oy, edge.end.y + oy],
                [edge.start.z + oz, edge.end.z + oz],
                color="darkgray",
                linewidth=0.3,
                alpha=0.6,
            )

    # Also show vertices as small points for additional detail
    if step.vertices:
        # Sample vertices if too many
        max_vertices = 500
        verts_to_plot = step.vertices[:max_vertices] if len(step.vertices) > max_vertices else step.vertices
        vx = [v.x + ox for v in verts_to_plot]
        vy = [v.y + oy for v in verts_to_plot]
        vz = [v.z + oz for v in verts_to_plot]
        ax.scatter(vx, vy, vz, c="coral", s=3, alpha=0.5, label="STEP vertices")

    # Plot footprint pads as 3D rectangles at Z=0
    for pad in footprint.pads:
        # Create rectangle vertices
        hw, hh = pad.width / 2, pad.height / 2
        z_pad = 0.05  # Slight offset for visibility
        verts = [
            [pad.x - hw, pad.y - hh, z_pad],
            [pad.x + hw, pad.y - hh, z_pad],
            [pad.x + hw, pad.y + hh, z_pad],
            [pad.x - hw, pad.y + hh, z_pad],
        ]
        color = "cyan" if pad.is_through_hole else "blue"
        poly = Poly3DCollection([verts], alpha=0.6, facecolor=color, edgecolor="darkblue")
        ax.add_collection3d(poly)

        # Draw drill hole cylinder for TH pads
        if pad.is_through_hole and pad.drill_size:
            r = pad.drill_size / 2
            theta = np.linspace(0, 2 * np.pi, 16)
            x_cyl = pad.x + r * np.cos(theta)
            y_cyl = pad.y + r * np.sin(theta)
            for z in [z_pad, -2.0]:
                ax.plot(x_cyl, y_cyl, z, color="black", linewidth=0.5)

    # Plot STEP bounding box as wireframe
    if step.bounding_box:
        bbox = step.bounding_box
        x0, y0, z0 = bbox.min.x + ox, bbox.min.y + oy, bbox.min.z + oz
        x1, y1, z1 = bbox.max.x + ox, bbox.max.y + oy, bbox.max.z + oz

        # Draw 12 edges of the bounding box
        edges = [
            ([x0, x1], [y0, y0], [z0, z0]),
            ([x0, x1], [y1, y1], [z0, z0]),
            ([x0, x1], [y0, y0], [z1, z1]),
            ([x0, x1], [y1, y1], [z1, z1]),
            ([x0, x0], [y0, y1], [z0, z0]),
            ([x1, x1], [y0, y1], [z0, z0]),
            ([x0, x0], [y0, y1], [z1, z1]),
            ([x1, x1], [y0, y1], [z1, z1]),
            ([x0, x0], [y0, y0], [z0, z1]),
            ([x1, x1], [y0, y0], [z0, z1]),
            ([x0, x0], [y1, y1], [z0, z1]),
            ([x1, x1], [y1, y1], [z0, z1]),
        ]
        for xs, ys, zs in edges:
            ax.plot(xs, ys, zs, color="red", linewidth=1.5)

    # Plot cylindrical pins
    for pin in step.vertical_pins:
        theta = np.linspace(0, 2 * np.pi, 12)
        x_cyl = pin.x + ox + pin.radius * np.cos(theta)
        y_cyl = pin.y + oy + pin.radius * np.sin(theta)
        z_top = step.bounding_box.max.z + oz if step.bounding_box else 5
        z_bot = step.bottom_face_z + oz if step.bottom_face_z is not None else 0
        ax.plot(x_cyl, y_cyl, [z_top] * len(theta), color="green", linewidth=1)
        ax.plot(x_cyl, y_cyl, [z_bot] * len(theta), color="green", linewidth=1)

    # Plot rectangular pins as 3D boxes
    for pin in step.rectangular_pins:
        x0, y0, z0 = pin.x + ox - pin.size_x / 2, pin.y + oy - pin.size_y / 2, pin.min_z + oz
        x1, y1, z1 = pin.x + ox + pin.size_x / 2, pin.y + oy + pin.size_y / 2, pin.max_z + oz

        # Draw box edges
        edges = [
            ([x0, x1], [y0, y0], [z0, z0]),
            ([x0, x1], [y1, y1], [z0, z0]),
            ([x0, x1], [y0, y0], [z1, z1]),
            ([x0, x1], [y1, y1], [z1, z1]),
            ([x0, x0], [y0, y1], [z0, z0]),
            ([x1, x1], [y0, y1], [z0, z0]),
            ([x0, x0], [y0, y1], [z1, z1]),
            ([x1, x1], [y0, y1], [z1, z1]),
            ([x0, x0], [y0, y0], [z0, z1]),
            ([x1, x1], [y0, y0], [z0, z1]),
            ([x0, x0], [y1, y1], [z0, z1]),
            ([x1, x1], [y1, y1], [z0, z1]),
        ]
        for xs, ys, zs in edges:
            ax.plot(xs, ys, zs, color="purple", linewidth=1.5)

    # Plot horizontal circles (useful for pin hole visualization)
    for circle in step.circles:
        # Only show horizontal circles (normal pointing up/down)
        if abs(circle.normal.z) > 0.9:
            theta = np.linspace(0, 2 * np.pi, 24)
            x_circle = circle.x + ox + circle.radius * np.cos(theta)
            y_circle = circle.y + oy + circle.radius * np.sin(theta)
            z_circle = circle.z + oz
            ax.plot(x_circle, y_circle, [z_circle] * len(theta), color="orange", linewidth=1.0, alpha=0.8)

    # Draw board plane
    all_x = [p.x for p in footprint.pads]
    all_y = [p.y for p in footprint.pads]
    if step.bounding_box:
        all_x.extend([step.bounding_box.min.x + ox, step.bounding_box.max.x + ox])
        all_y.extend([step.bounding_box.min.y + oy, step.bounding_box.max.y + oy])

    if all_x and all_y:
        margin = 2
        board_verts = [
            [min(all_x) - margin, min(all_y) - margin, 0],
            [max(all_x) + margin, min(all_y) - margin, 0],
            [max(all_x) + margin, max(all_y) + margin, 0],
            [min(all_x) - margin, max(all_y) + margin, 0],
        ]
        board = Poly3DCollection([board_verts], alpha=0.2, facecolor="green", edgecolor="darkgreen")
        ax.add_collection3d(board)

    # Set viewing angle (isometric-ish)
    ax.view_init(elev=25, azim=-60)
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_zlabel("Z (mm)")

    # Equal aspect ratio
    if all_x and all_y:
        max_range = max(max(all_x) - min(all_x), max(all_y) - min(all_y))
        if step.bounding_box:
            max_range = max(max_range, step.bounding_box.size.z)
        mid_x = (min(all_x) + max(all_x)) / 2
        mid_y = (min(all_y) + max(all_y)) / 2
        mid_z = oz if step.bounding_box is None else (step.bounding_box.min.z + step.bounding_box.max.z) / 2 + oz
        ax.set_xlim(mid_x - max_range / 2 - 2, mid_x + max_range / 2 + 2)
        ax.set_ylim(mid_y - max_range / 2 - 2, mid_y + max_range / 2 + 2)
        ax.set_zlim(-5, mid_z + max_range / 2 + 2)


def _plot_footprint_and_step_xy(ax, step, footprint, ox, oy):
    """Helper to plot footprint and STEP data in X/Y top view with detailed wireframe"""
    import matplotlib.patches as mpatches
    from matplotlib.patches import Polygon

    # Plot projected edges (X/Y projection of all edges - detailed wireframe)
    if step.edges:
        max_edges = 1000
        edges_to_plot = step.edges[:max_edges] if len(step.edges) > max_edges else step.edges
        for edge in edges_to_plot:
            ax.plot(
                [edge.start.x + ox, edge.end.x + ox],
                [edge.start.y + oy, edge.end.y + oy],
                color="lightgray",
                linewidth=0.3,
                alpha=0.5,
                zorder=0,
            )

    # Plot STEP bounding box as clean outline (silhouette can be spiky)
    # The edges provide the detail, bbox provides the boundary
    if step.bounding_box:
        bbox = step.bounding_box
        rect = mpatches.Rectangle(
            (bbox.min.x + ox, bbox.min.y + oy),
            bbox.size.x,
            bbox.size.y,
            facecolor="lightcoral",
            edgecolor="red",
            alpha=0.15,
            linewidth=2,
            zorder=1,
        )
        ax.add_patch(rect)
    elif step.vertices:
        # Fallback to point cloud if no silhouette
        vx = [v.x + ox for v in step.vertices]
        vy = [v.y + oy for v in step.vertices]
        ax.scatter(vx, vy, c="lightcoral", s=1, alpha=0.3, zorder=1)

    # Plot rectangular pins
    for pin in step.rectangular_pins:
        rect = mpatches.Rectangle(
            (pin.x + ox - pin.size_x / 2, pin.y + oy - pin.size_y / 2),
            pin.size_x,
            pin.size_y,
            facecolor="purple",
            edgecolor="darkviolet",
            alpha=0.5,
            zorder=2,
        )
        ax.add_patch(rect)

    # Plot footprint pads
    for pad in footprint.pads:
        color = "blue" if not pad.is_through_hole else "cyan"
        rect = mpatches.Rectangle(
            (pad.x - pad.width / 2, pad.y - pad.height / 2),
            pad.width,
            pad.height,
            angle=pad.rotation,
            facecolor=color,
            edgecolor="darkblue",
            alpha=0.5,
            zorder=3,
        )
        ax.add_patch(rect)

        # Draw drill hole for TH pads
        if pad.is_through_hole and pad.drill_size:
            circle = mpatches.Circle(
                (pad.x, pad.y),
                pad.drill_size / 2,
                facecolor="white",
                edgecolor="black",
                zorder=4,
            )
            ax.add_patch(circle)

    # Plot STEP bounding box (with offset)
    if step.bounding_box:
        bbox = step.bounding_box
        rect = mpatches.Rectangle(
            (bbox.min.x + ox, bbox.min.y + oy),
            bbox.size.x,
            bbox.size.y,
            facecolor="none",
            edgecolor="red",
            linewidth=2,
            zorder=2,
        )
        ax.add_patch(rect)

    # Plot STEP pins (with offset)
    for pin in step.vertical_pins:
        circle = mpatches.Circle(
            (pin.x + ox, pin.y + oy),
            pin.radius,
            facecolor="green",
            edgecolor="darkgreen",
            alpha=0.5,
            zorder=5,
        )
        ax.add_patch(circle)

    # Auto-scale
    all_x = [p.x for p in footprint.pads]
    all_y = [p.y for p in footprint.pads]
    if step.bounding_box:
        all_x.extend([step.bounding_box.min.x + ox, step.bounding_box.max.x + ox])
        all_y.extend([step.bounding_box.min.y + oy, step.bounding_box.max.y + oy])

    if all_x and all_y:
        margin = 2
        ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
        ax.set_ylim(min(all_y) - margin, max(all_y) + margin)


def _plot_side_view_xz(ax, step, footprint, ox, oz):
    """Helper to plot side view (X-Z plane) showing Z alignment"""
    import matplotlib.patches as mpatches

    # Plot STEP bounding box as side silhouette (clean rectangle)
    # Edges provide the detail
    if step.bounding_box:
        bbox = step.bounding_box
        rect = mpatches.Rectangle(
            (bbox.min.x + ox, bbox.min.z + oz),
            bbox.size.x,
            bbox.size.z,
            facecolor="lightcoral",
            edgecolor="red",
            alpha=0.2,
            linewidth=2,
            zorder=1,
        )
        ax.add_patch(rect)
    elif step.vertices:
        # Fallback to point cloud
        vx = [v.x + ox for v in step.vertices]
        vz = [v.z + oz for v in step.vertices]
        ax.scatter(vx, vz, c="lightcoral", s=1, alpha=0.3, zorder=1)

    # Draw board as a thick line at Z=0
    all_x = [p.x for p in footprint.pads]
    if step.bounding_box:
        all_x.extend([step.bounding_box.min.x + ox, step.bounding_box.max.x + ox])

    if all_x:
        board_margin = 5
        board_left = min(all_x) - board_margin
        board_right = max(all_x) + board_margin

        # Draw board surface representation (copper layer ~0.035mm, but exaggerate for visibility)
        board_thickness = 1.6  # Standard PCB thickness
        board = mpatches.Rectangle(
            (board_left, -board_thickness),
            board_right - board_left,
            board_thickness,
            facecolor="darkgreen",
            edgecolor="black",
            alpha=0.3,
            label="PCB",
        )
        ax.add_patch(board)

    # Draw through-hole pins extending below board
    for pad in footprint.pads:
        if pad.is_through_hole and pad.drill_size:
            # TH pins extend below the board
            pin_length_below = 2.5  # Typical TH pin extension
            rect = mpatches.Rectangle(
                (pad.x - pad.drill_size / 4, -pin_length_below),
                pad.drill_size / 2,
                pin_length_below,
                facecolor="gold",
                edgecolor="darkgoldenrod",
                alpha=0.7,
            )
            ax.add_patch(rect)

    # Draw STEP bounding box in X-Z plane (with offsets)
    if step.bounding_box:
        bbox = step.bounding_box
        rect = mpatches.Rectangle(
            (bbox.min.x + ox, bbox.min.z + oz),
            bbox.size.x,
            bbox.size.z,
            facecolor="lightcoral",
            edgecolor="red",
            linewidth=2,
            alpha=0.3,
        )
        ax.add_patch(rect)

        # Draw bottom face Z as a horizontal line
        if step.bottom_face_z is not None:
            bottom_z = step.bottom_face_z + oz
            ax.axhline(
                y=bottom_z,
                color="orange",
                linewidth=2,
                linestyle="--",
                alpha=0.8,
            )
            ax.annotate(
                f"Bottom face: {bottom_z:.2f}mm",
                xy=(bbox.min.x + ox + bbox.size.x / 2, bottom_z),
                xytext=(0, 10),
                textcoords="offset points",
                ha="center",
                fontsize=8,
                color="darkorange",
            )

    # Draw STEP vertical pins in X-Z view
    for pin in step.vertical_pins:
        # Estimate pin height from bounding box or use default
        pin_top = step.bounding_box.max.z + oz if step.bounding_box else 5
        pin_bottom = step.bottom_face_z + oz if step.bottom_face_z is not None else 0
        pin_height = pin_top - pin_bottom

        rect = mpatches.Rectangle(
            (pin.x + ox - pin.radius, pin_bottom),
            pin.radius * 2,
            pin_height,
            facecolor="green",
            edgecolor="darkgreen",
            alpha=0.5,
        )
        ax.add_patch(rect)

    # Draw rectangular pins in X-Z view
    for pin in step.rectangular_pins:
        rect = mpatches.Rectangle(
            (pin.x + ox - pin.size_x / 2, pin.min_z + oz),
            pin.size_x,
            pin.max_z - pin.min_z,
            facecolor="purple",
            edgecolor="darkviolet",
            alpha=0.5,
        )
        ax.add_patch(rect)

    # Auto-scale
    all_z = [0]  # Board surface
    if step.bounding_box:
        all_z.extend([step.bounding_box.min.z + oz, step.bounding_box.max.z + oz])
    if step.bottom_face_z is not None:
        all_z.append(step.bottom_face_z + oz)

    # Include TH pin extensions
    if footprint.through_hole_pads:
        all_z.append(-2.5)

    if all_x and all_z:
        margin_x = 2
        margin_z = 1
        ax.set_xlim(min(all_x) - margin_x, max(all_x) + margin_x)
        ax.set_ylim(min(all_z) - margin_z, max(all_z) + margin_z)


def run_test():
    """Run on test data"""
    test_dir = ROOT / "src" / "faebryk" / "core" / "zig" / "src" / "step" / "testdata"

    test_cases = [
        # SMD passives
        ("R0402_L1.0-W0.5-H0.4.step", "R0402.kicad_mod"),
        ("C0402_L1.0-W0.5-H0.5.step", "C0402.kicad_mod"),
        ("C0805_L2.0-W1.3-H1.3.step", "C0805.kicad_mod"),
        ("LED0603-RD-YELLOW.step", "LED0603-RD-YELLOW.kicad_mod"),
        ("CAP-SMD_BD6.3-L6.6-W6.6-H7.7.step", "CAP-SMD_BD6.3-L6.6-W6.6-LS7.6-FD.kicad_mod"),
        # ICs
        ("SOT-89-3_L4.3-W2.5-H1.6-LS4.1-P1.50.step", "SOT-89-3_L4.5-W2.5-P1.50-LS4.1-TR.kicad_mod"),
        # Through-hole
        ("HDR-M-2.54_2x5.step", "HDR-2x5.kicad_mod"),
        ("PWRM-TH_IBXX05S-2WR3.step", "PWRM-TH_IBXX05S-2WR3.kicad_mod"),
        ("CONN-TH_2P-P5.08_DB2ERC-5.08-2P-BK.step", "CONN-TH_2P-P5.08_DB2ERC-5.08-2P-BK.kicad_mod"),
        ("SW-TH_EC12D1524403-L12.5-W11.7-H17.5-P11.1-LS14.1.step", "SW-TH_EC12D1524403.kicad_mod"),
    ]

    for step_name, fp_name in test_cases:
        step_path = test_dir / step_name
        fp_path = test_dir / fp_name

        if not step_path.exists():
            print(f"STEP file not found: {step_path}")
            continue
        if not fp_path.exists():
            print(f"Footprint not found: {fp_path}")
            continue

        print(f"\n{'='*60}")
        print(f"Testing: {step_name} + {fp_name}")
        print("=" * 60)

        # Analyze files
        print("\nAnalyzing STEP file...")
        step_analysis = analyze_step_file(step_path)
        if not step_analysis:
            print("Failed to analyze STEP file")
            continue

        print(f"  Entities: {step_analysis.entities}")
        if step_analysis.size:
            print(
                f"  Size: {step_analysis.size.x:.2f} x {step_analysis.size.y:.2f} x {step_analysis.size.z:.2f} mm"
            )
        print(f"  Bottom Z: {step_analysis.bottom_face_z}")
        print(f"  Cylindrical pins: {len(step_analysis.vertical_pins)}")
        print(f"  Rectangular pins: {len(step_analysis.rectangular_pins)}")
        print(f"  Edges: {len(step_analysis.edges)}, Horizontal planes: {len(step_analysis.horizontal_planes)}")
        print(f"  Silhouette points: XY={len(step_analysis.silhouette_xy)}, XZ={len(step_analysis.silhouette_xz)}")

        print("\nAnalyzing footprint...")
        fp_analysis = analyze_footprint(fp_path)
        print(f"  Pads: {len(fp_analysis.pads)}")
        print(f"  Through-hole: {len(fp_analysis.through_hole_pads)}")
        print(f"  SMD: {len(fp_analysis.smd_pads)}")

        # Compute alignment
        print("\nComputing alignment...")
        alignment = compute_alignment(step_analysis, fp_analysis)
        print(f"  Method: {alignment.method}")
        print(f"  Confidence: {alignment.confidence:.2f}")
        print(
            f"  Offset: ({alignment.offset_x:.3f}, {alignment.offset_y:.3f}, {alignment.offset_z:.3f})"
        )

        # Collision check
        has_collision, collisions = check_collision(
            step_analysis, fp_analysis,
            alignment.offset_x, alignment.offset_y, alignment.offset_z
        )
        if has_collision:
            print(f"  Collisions detected: {len(collisions)}")
            for c in collisions[:3]:  # Show first 3
                print(f"    - {c}")
        else:
            print("  Collision check: PASSED")

        # Visualize
        output_path = test_dir / f"alignment_{step_name.replace('.step', '.png')}"
        visualize_alignment(step_analysis, fp_analysis, alignment, output_path)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "--test":
        run_test()
    elif len(sys.argv) >= 3:
        step_path = Path(sys.argv[1])
        fp_path = Path(sys.argv[2])

        if not step_path.exists():
            print(f"STEP file not found: {step_path}")
            sys.exit(1)
        if not fp_path.exists():
            print(f"Footprint not found: {fp_path}")
            sys.exit(1)

        step_analysis = analyze_step_file(step_path)
        if not step_analysis:
            print("Failed to analyze STEP file")
            sys.exit(1)

        fp_analysis = analyze_footprint(fp_path)
        alignment = compute_alignment(step_analysis, fp_analysis)

        print(f"Alignment result:")
        print(f"  Method: {alignment.method}")
        print(f"  Confidence: {alignment.confidence:.2f}")
        print(
            f"  Offset: ({alignment.offset_x:.3f}, {alignment.offset_y:.3f}, {alignment.offset_z:.3f})"
        )
        print(f"  Rotation: {alignment.rotation}°")

        visualize_alignment(step_analysis, fp_analysis, alignment)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
