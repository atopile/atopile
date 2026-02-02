# STEP File Parser Specification

## Overview

A Zig-native parser for ISO 10303-21 (STEP Part 21) files, focused on extracting geometric and topological data from 3D component models for PCB alignment.

## Goals

1. **Round-trip fidelity** - Parse and dump STEP files without data loss
2. **Fast queries** - Bounding box, pin detection, bottom face in O(n) or better
3. **Precise** - Full floating-point precision, suitable for sub-0.01mm alignment
4. **Python API** - Match the existing sexp/footprint parser patterns
5. **Lightweight** - No external dependencies, pure Zig

## Non-Goals (for now)

- Full AP214/AP203 schema validation
- Tessellation/mesh generation
- Boolean operations on solids
- NURBS surface evaluation

---

## Test Parts

Selected for coverage of different component types:

| Part | Type | Lines | Notes |
|------|------|-------|-------|
| `UNI_ROYAL_0402WGF1001TCE/R0402_L1.0-W0.5-H0.4.step` | SMD Resistor | 15,039 | Simple rectangular body |
| `Samsung_Electro_Mechanics_CL10A106MQ8NNNC/C0603_L1.6-W0.8-H0.8.step` | SMD Capacitor | 19,867 | Rounded edges |
| `Texas_Instruments_SN74LVC1G07DBVR/SOT-23-5_L2.9-W1.6-H1.1-LS2.8-P0.95.step` | IC (SOT-23) | 37,939 | SMD with leads |
| `XIAMEN_FARATRONIC_C232A475J6SC000/CAP-TH_L17.5-W8.5-H13.5-P15.0.step` | TH Capacitor | 14,919 | Through-hole with 2 pins |
| `CJT_A2541WV_2x5P/HDR-M-2.54_2x5.step` | TH Header | 23,621 | 10 pins in 2x5 grid |
| `YLPTEC_B0524S_2WR3/PWRM-TH_IBXX05S-2WR3.step` | Power Module | 17,780 | Through-hole with pins |
| `Texas_Instruments_TPS7A4700RGWT/VQFN-20_L5.0-W5.0-H1.0-P0.65.step` | IC (QFN) | 29,325 | Complex leadless package |

Source directory: `/Users/narayanpowderly/projects/dsp/projects/dsp/parts/`

---

## STEP File Format

### Structure

```
ISO-10303-21;
HEADER;
FILE_DESCRIPTION((...), '2;1');
FILE_NAME('name.step', '2022-07-01T06:11:46', ...);
FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));
ENDSEC;

DATA;
#1 = CARTESIAN_POINT('NONE', (0.0, 0.0, 0.0));
#2 = DIRECTION('NONE', (0.0, 0.0, 1.0));
#3 = AXIS2_PLACEMENT_3D('NONE', #1, #2, #3);
...
ENDSEC;
END-ISO-10303-21;
```

### Entity Reference Pattern

- Entities are numbered: `#123`
- References use entity numbers: `EDGE_CURVE('NONE', #45, #67, #89, .T.)`
- Complex types use parentheses: `(NAMED_UNIT(*) SI_UNIT($, .METRE.) LENGTH_UNIT())`

### Key Entity Types

**Geometry (primitives)**
- `CARTESIAN_POINT` - 3D point coordinates
- `DIRECTION` - Unit vector
- `VECTOR` - Direction with magnitude
- `AXIS2_PLACEMENT_3D` - Coordinate system (location + Z axis + X axis)

**Curves**
- `LINE` - Point + direction
- `CIRCLE` - Axis placement + radius
- `B_SPLINE_CURVE_WITH_KNOTS` - NURBS curve

**Surfaces**
- `PLANE` - Axis placement (normal = Z axis)
- `CYLINDRICAL_SURFACE` - Axis placement + radius
- `SPHERICAL_SURFACE` - Axis placement + radius
- `B_SPLINE_SURFACE_WITH_KNOTS` - NURBS surface

**Topology (B-Rep)**
- `VERTEX_POINT` - Vertex referencing a point
- `EDGE_CURVE` - Edge with start/end vertices and underlying curve
- `ORIENTED_EDGE` - Edge with direction flag
- `EDGE_LOOP` - Closed loop of oriented edges
- `FACE_OUTER_BOUND` / `FACE_BOUND` - Loop bounding a face
- `ADVANCED_FACE` - Face with bounds and underlying surface
- `CLOSED_SHELL` - Collection of faces forming a closed volume
- `MANIFOLD_SOLID_BREP` - Solid body from a closed shell

**Product Structure**
- `PRODUCT` - Named product
- `PRODUCT_DEFINITION` - Product version/configuration
- `SHAPE_REPRESENTATION` - Geometric representation
- `SHAPE_DEFINITION_REPRESENTATION` - Links product to geometry

**Styling (preserve for visualization)**
- `COLOUR_RGB` - Color values
- `STYLED_ITEM` - Links styling to geometry
- `PRESENTATION_STYLE_ASSIGNMENT` - Style definitions

---

## Architecture

### File Layout

```
src/faebryk/core/zig/src/step/
├── tokenizer.zig      # STEP tokenizer
├── parser.zig         # Entity parsing and reference resolution
├── entities.zig       # Entity type definitions
├── queries.zig        # Geometric queries (bbox, cylinders, etc.)
├── writer.zig         # STEP file serialization
└── lib.zig            # Public API

src/faebryk/core/zig/src/python/step/
├── step_py.zig        # Python module generation
└── step_pyi.zig       # Type stub generation
```

### Core Data Structures

```zig
// Primitives
pub const Point3D = struct { x: f64, y: f64, z: f64 };
pub const Direction3D = struct { x: f64, y: f64, z: f64 };
pub const Vector3D = struct { direction: *Direction3D, magnitude: f64 };

pub const Axis2Placement3D = struct {
    location: *Point3D,
    axis: ?*Direction3D,      // Z direction (default: 0,0,1)
    ref_direction: ?*Direction3D,  // X direction (default: 1,0,0)
};

// Curves
pub const Line = struct { point: *Point3D, direction: *Vector3D };
pub const Circle = struct { position: *Axis2Placement3D, radius: f64 };
pub const BSplineCurve = struct {
    degree: u8,
    control_points: []*Point3D,
    knots: []f64,
    knot_multiplicities: []u32,
};

// Surfaces
pub const Plane = struct { position: *Axis2Placement3D };
pub const CylindricalSurface = struct { position: *Axis2Placement3D, radius: f64 };
pub const SphericalSurface = struct { position: *Axis2Placement3D, radius: f64 };

// Topology
pub const Vertex = struct { point: *Point3D };
pub const Edge = struct {
    start: *Vertex,
    end: *Vertex,
    curve: CurveUnion,
    same_sense: bool,
};
pub const Face = struct {
    bounds: []FaceBound,
    surface: SurfaceUnion,
    same_sense: bool,
};
pub const Shell = struct { faces: []*Face };
pub const Solid = struct {
    name: []const u8,
    shell: *Shell,
};

// Top-level
pub const StepFile = struct {
    header: Header,
    solids: []*Solid,
    colors: []Color,
    // ... other entities
};
```

### Query API

```zig
pub const BoundingBox = struct {
    min: Point3D,
    max: Point3D,
};

pub const Cylinder = struct {
    position: Axis2Placement3D,
    radius: f64,
    height: ?f64,  // computed from bounding edges
};

pub fn bounding_box(file: *StepFile) BoundingBox;
pub fn find_cylinders(file: *StepFile, min_radius: f64, max_radius: f64) []Cylinder;
pub fn bottom_face_z(file: *StepFile) f64;
pub fn centroid(file: *StepFile) Point3D;
```

---

## Python API

```python
from faebryk.core.zig.gen import step

# Load/dump
model = step.loads(path.read_text())
text = step.dumps(model)

# Properties
print(model.header.file_name)
print(len(model.solids))

# Queries
bbox = model.bounding_box()
print(f"Size: {bbox.max.x - bbox.min.x} x {bbox.max.y - bbox.min.y} x {bbox.max.z - bbox.min.z}")

bottom_z = model.bottom_face_z()
print(f"Bottom face at Z={bottom_z}")

cylinders = model.find_cylinders(min_radius=0.1, max_radius=0.6)
for cyl in cylinders:
    if abs(cyl.axis.z) > 0.99:  # Vertical cylinder = pin
        print(f"Pin at ({cyl.position.x}, {cyl.position.y}), r={cyl.radius}")
```

---

## Implementation Plan

### Phase 1: Tokenizer & Basic Parser ✅ COMPLETE
- [x] Implement STEP tokenizer (entity IDs, types, parameters, strings, numbers)
- [x] Parse header section (FILE_DESCRIPTION, FILE_NAME, FILE_SCHEMA)
- [x] Parse DATA section into entity map
- [x] Entity reference storage (resolution via lookup)

### Phase 2: Core Geometry ✅ COMPLETE
- [x] CARTESIAN_POINT (extraction for queries)
- [x] DIRECTION (extraction for queries)
- [x] AXIS2_PLACEMENT_3D (extraction for queries)
- [x] Compute bounding box from all points
- [ ] VECTOR (stored but not specialized)
- [ ] LINE, CIRCLE (stored but not specialized)

### Phase 3: Surfaces ✅ PARTIAL
- [x] PLANE (detection for bottom face)
- [x] CYLINDRICAL_SURFACE (detection for pins)
- [ ] SPHERICAL_SURFACE (stored but not specialized)
- [ ] B_SPLINE_CURVE_WITH_KNOTS (stored as raw)
- [ ] B_SPLINE_SURFACE_WITH_KNOTS (stored as raw)

### Phase 4: Topology (Stored but not specialized)
- [ ] VERTEX_POINT
- [ ] EDGE_CURVE
- [ ] ORIENTED_EDGE
- [ ] EDGE_LOOP
- [ ] FACE_OUTER_BOUND, FACE_BOUND
- [ ] ADVANCED_FACE
- [ ] CLOSED_SHELL
- [ ] MANIFOLD_SOLID_BREP

### Phase 5: Product & Styling (Stored but not specialized)
- [ ] PRODUCT, PRODUCT_DEFINITION
- [ ] SHAPE_REPRESENTATION
- [ ] COLOUR_RGB
- [ ] STYLED_ITEM

### Phase 6: Writer (Round-trip) ✅ COMPLETE
- [x] Serialize entities back to STEP format
- [x] Preserve entity order
- [x] Round-trip tests pass (7/7 test files)

### Phase 7: Queries ✅ COMPLETE
- [x] bounding_box()
- [x] find_cylinders()
- [x] bottom_face_z()
- [x] centroid()
- [x] Unit conversion (SI_UNIT detection)

### Phase 8: Python Alignment Tool ✅ PARTIAL
- [x] analyze.zig - Standalone JSON analyzer binary
- [x] step_alignment_tool.py - Python alignment tool using Zig analyzer
- [x] SMD centroid alignment strategy
- [x] Through-hole centroid alignment strategy (cylindrical pins only)
- [x] Bounding box fallback alignment
- [x] Visualization with matplotlib
- [ ] Rectangular pin detection (for headers)
- [ ] SMD pad boundary detection
- [ ] Proper Python bindings (step_py.zig)

---

## Design Decisions

### Units
- All coordinates normalized to millimeters
- Parse SI_UNIT to determine source units and convert

### Multi-solid Models
- Expose all MANIFOLD_SOLID_BREP entities as separate solids
- Provide helper to get "main" solid (largest by bounding box)

### Colors
- Preserve COLOUR_RGB values
- Link colors to faces via STYLED_ITEM chain

### Precision
- Store all floats as f64
- On dump, use same precision as input (track original string representation)

### Unknown Entities
- TBD: Store as opaque or error?

### Error Handling
- Detailed error context with line/column (match sexp pattern)
- Lenient parsing for SolidWorks quirks

---

## Test Plan

### Round-trip Tests
For each test part:
1. Parse STEP file
2. Dump back to string
3. Parse dumped string
4. Compare: entity counts, point coordinates, topology structure

### Query Tests
For each test part, verify:
1. Bounding box matches expected dimensions (from filename hints like "L1.6-W0.8-H0.8")
2. Through-hole parts have expected pin count
3. SMD parts have bottom_face_z near 0

### Expected Results (VERIFIED)

| Part | BBox (mm) | Bottom Z | Cylinders | Pin Positions |
|------|-----------|----------|-----------|---------------|
| R0402 | 1.00 x 0.50 x 0.50 | 0.0 | 0 | N/A (SMD) |
| C0603 | 4.00 x 0.80 x 0.80 | -0.4 | 0 | N/A (SMD) |
| SOT-23-5 | 3.01 x 2.90 x 1.51 | 0.1 | 17 (2 vertical) | (-0.36, 1.01) |
| CAP-TH | 17.50 x 8.50 x 17.51 | -4.0 | 4 (4 vertical) | ±7.5mm spacing ✓ |
| HDR-2x5 | 14.94 x 5.08 x 12.12 | -3.0 | 0 | Rectangular pins (not cylinders) |
| Power Module | 19.65 x 7.05 x 13.80 | -3.5 | 10 (4 vertical) | Corner pins |
| VQFN-20 | 5.02 x 5.02 x 1.02 | -0.02 | 22 (22 vertical) | QFN leads |

**Notes:**
- All 7 files parse successfully
- Round-trip (parse → dump → parse) preserves entity count
- Bottom Z represents lowest horizontal plane
- Cylinder detection finds CYLINDRICAL_SURFACE entities, radius 0.1-1.0mm
- Header (HDR-2x5) has rectangular pins, not cylindrical

---

## Open Questions (Resolved)

1. **Test file location** - Reference external path for now; can copy later if needed
2. **Float precision** - Preserve original string representation for round-trip
3. **Unknown entities** - Store as generic Parameter union (preserves all data)

## Implementation Status

**Current State:** Core parser complete with round-trip support and geometric queries.

**Files:**
```
src/faebryk/core/zig/src/step/
├── tokenizer.zig    # STEP tokenizer (ISO 10303-21 format)
├── ast.zig          # Entity and parameter types
├── parser.zig       # Parser for STEP files
├── writer.zig       # Serializer for round-trip
├── queries.zig      # Geometric queries (bbox, cylinders, bottom_z)
├── lib.zig          # Public API
└── tests.zig        # Test runner
```

**Tested on 7 real JLC STEP files - all passing.**

---

## References

- ISO 10303-21 (STEP Part 21 - Clear Text Encoding)
- ISO 10303-42 (Geometric and Topological Representation)
- AP214 (Automotive Design)
- Existing sexp parser: `src/faebryk/core/zig/src/sexp/`
