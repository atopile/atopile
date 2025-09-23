# PCB Graph MVP Specification

## Rules of atopile

- Instrumentation is everything
- The only datastructure is the graph
- Code is a graph
- The only algorithm is a BFS
- Edge cases are the result of bad abstractions
- Write to be read
- Programming is naming

## Objective

Convert the internal PCB representation from ad-hoc structs into a graph-first model that can round-trip load and dump KiCad `.kicad_pcb` files. The MVP should demonstrate feature parity with the existing exporter for the covered primitives while fitting naturally into the broader Faebryk graph ecosystem.

## Motivation

- Reuse the graph infrastructure that already powers other build steps, making PCB data interoperable with traits, solvers, and future design automation.
- Unlock performant transformations and DRC pipelines by moving heavy graph rewrites into the C++ core once the data is graph-shaped.
- Provide a sustainable foundation for richer tooling (custom DRC, layout reuse, stackup planning) instead of mirroring KiCad’s limited data model.

## Scope

### In scope for the MVP

- Load a KiCad PCB into the new graph representation and persist the content faithfully back to KiCad (`import → transform → export`).
- Model the full layer stack, including global ordering and per-primitive layer membership. Preserve KiCad-specific data via dedicated subnodes (e.g. `KicadLayerNode`) while keeping the primary layer model backend-agnostic.
- Represent all commonly used PCB primitives observed in the current layouts:
  - Nets as dedicated graph nodes connected to any copper-carrying geometry.
  - Segments, arcs, circles, rectangles, vias, zones, keepouts, board outlines, text, graphics, footprints (with pads, 3D models, local graphics), and groups.
  - Module/footprint placement hierarchy so child primitives inherit relative coordinate frames (e.g. Board XY → Footprint XY → Pad XY).
- Preserve numeric parameters as graph `Parameter`s where possible so constraints/expressions can be solved later rather than flattened to literals.
- Ensure UUIDs, properties, plot settings, and other KiCad metadata survive the roundtrip when present.

### Out of scope (for now)

- Non-KiCad backends (but the design should avoid blocking them).
- Advanced electrical/thermal analysis or solver integration beyond keeping parameters symbolic.
- UI/visualization improvements beyond what `pcbviz.py` already provides. # dont really care about this, we can jsut use KiCAD

## References & Current State

- **Existing transformer**: `src/faebryk/exporters/pcb/kicad/transformer.py` currently materialises PCB primitives from graph data into KiCad dataclasses. It covers a wide surface: footprints, pads, zones, text, board setup, plot parameters, etc. The MVP graph should be expressive enough to supply the same information back to this transformer (or its successor).
- **Prototype graph**: `src/faebryk/core/pcbgraph.py` introduces `LineNode`, `ArcNode`, `CircleNode`, `RectangleNode`, `ViaNode`, `NetNode`, `LayerNode`, and helper constructors. It demonstrates:
  - Using `Parameter.alias_is` to keep geometry literals symbolic (`new_arc`, `new_line`).
  - Attaching KiCad-specific data through child nodes (`KicadLayerNode` storing the layer enum string).
  - Sharing a `NetNode` across multiple primitives using `.connect()` (e.g. the demo ties `line_a`, `line_b`, and `via_a` to one net).
  - Basic relative geometry by reusing child `XYRNode`s (via pads reference the via centre despite lacking a full hierarchy yet).
- **Real-world example**: `examples/esp32_minimal/layouts/esp32_minimal/esp32_minimal.kicad_pcb` illustrates additional constructs we must handle: multi-layer stack definitions, board setup metadata, footprints with nested graphics/text/pads, netclass assignments, zones with polygons + arcs, keepout rules, drill/plot configs, and user properties.

## Graph Representation Guidelines

1. **Hierarchy & Coordinate Frames**

   - Use nested `XYRNode`s to express relative placement: the board node anchors the global frame; footprints attach their own `XYRNode`; pads inherit from the footprint, etc.
   - Allow optional absolute anchors for cases where KiCad stores world coordinates; retain relative offsets in parallel when available. # we dont want absolute anchors, the XYRNode in question should just have the PCB XYR as its parent if it is 'absolute'

2. **Layers & Stackup**

   - Model a stackup tree (`StackupNode` or similar) that captures ordering, material, thickness, and relationships (above/below). Link primitives’ `LayerNode`s into this structure.
   - Preserve KiCad layer identifiers via child `KicadLayerNode`s so exporting back is lossless.

3. **Nets**

   - Each electrical net maps to one `NetNode`. Geometry attaches by connecting to the net (e.g. `net.connect(trace, via)`). Store net names/ids as literal `Parameter`s rather than enums to accommodate arbitrary user nets.

4. **Parameters & Constraints**

   - Geometry, stackup, and property values should be `Parameter`s wherever feasible (line width, via drill, solder mask clearances). Keep solver-friendly relationships (`pad.radius.alias_is(via.pad_diameter / 2)`) instead of baking numbers.

5. **Metadata**
   - Represent KiCad-specific metadata (footprint properties, text effects, zone fill rules, net classes, groups) via dedicated child nodes/parameters rather than overloading generic ones. Keep UUIDs to support incremental sync.

## Component Representation

- **Board Root (`PCBNode`)**
  - Owns global stackup, board outline, fabrication parameters, and top-level UUID/project metadata.
  - Serves as the parent frame for every placement node; absolute coordinates resolve against this origin.
- **Footprint Nodes**
  - Wrap KiCad footprints and future backend footprints; hold identifiers (`lib_id`, reference, value), placement pose (`XYRNode`), locked state, and attributes (smd/tht, through-hole plating, etc.).
  - Contain child collections for pads, local graphics (silk/courtyard/fab lines), reference/value text nodes, 3D model references, and footprint-level properties.
  - KiCad-specific data (library linkage, locked state, original footprint blob) stored in child `KicadFootprintNode` to maintain clean separation of concerns.
- **Pad Nodes**
  - Capture pad stack geometry (shape, size, drill, layers), paste/mask settings, round-rect ratio, tenting flags, castellations, and clearance overrides.
  - Connect to the owning `NetNode` and the footprint pose for relative placement. Support stacked pads via child pad nodes referencing the same pose.
- **Component Metadata Nodes**
  - Generic `PropertyNode`/`AttributeNode` pairs for manufacturer data, per-footprint parameters, and constraints (e.g. pick-and-place rotation locks).
  - Links to documentation (datasheet URLs) and BOM-relevant fields should retain formatting and visibility flags.
- **Mechanical & Visual Primitives**
  - Lines/arcs/circles/rectangles attach either at board level or inside footprints to model silks, mechanical outlines, keepouts, and user drawings.
  - Text nodes share placement semantics with other geometry and expose font/effects parameters for KiCad and future targets.

Documenting these nodes alongside their child parameters will help the importer/exporter stay symmetric and makes it easier to extend component modelling with new traits (e.g. pick-and-place metadata).

## Current Construction Patterns

The implementation provides helper functions and direct node construction patterns:

```python
# Direct primitive construction (from pcbgraph.py helpers)
line = new_line(x0, y0, x1, y1, width, layer=KicadLayer.F_Cu)
arc = new_arc(x0, y0, mx, my, x1, y1, width, layer=KicadLayer.F_SilkS)
circle = new_circle(cx, cy, radius, layer=KicadLayer.F_SilkS)
rectangle = new_rectangle(sx, sy, ex, ey, layer=KicadLayer.F_SilkS)
via = new_via(cx, cy, hole_size, pad_diameter)

# Net connectivity
net = NetNode()
net.name.value.alias_is("VCC")
net.net_id.alias_is(1)
net.connect(line, via)  # Connect multiple primitives to same net
```

```python
# Manual node construction with full parameter control
line = LineNode()
line.start.x.alias_is(x0)
line.start.y.alias_is(y0)
line.end.x.alias_is(x1)
line.end.y.alias_is(y1)
line.width.alias_is(track_width)

# Layer assignment via KiCad-specific child node
kicad_layer = KicadLayerNode()
line.layer.add(kicad_layer, name="kicad")
kicad_layer.name.value.alias_is(KicadLayer.F_Cu)
```

```python
# Polygon construction with points and arcs
polygon = PolygonNode()
polygon.uuid.alias_is("polygon-uuid-123")

# Add points to form the polygon outline
point1 = XYRNode()
point1.x.alias_is(0.0)
point1.y.alias_is(0.0)
polygon.add(point1)

point2 = XYRNode()
point2.x.alias_is(10.0)
point2.y.alias_is(0.0)
polygon.add(point2)

# Add an arc segment
arc = ArcNode()
arc.start.x.alias_is(10.0)
arc.start.y.alias_is(0.0)
arc.center.x.alias_is(10.0)
arc.center.y.alias_is(5.0)
arc.end.x.alias_is(0.0)
arc.end.y.alias_is(10.0)
arc.width.alias_is(0.0)  # Polygon outlines have no stroke width
polygon.add(arc)

# Connect elements to form the ring topology
point1.connect(point2)
point2.connect(arc)
arc.connect(point1)  # Close the loop
```

```python
# Import/Export pipeline usage
from atopile.pcb_transformer import load_pcb_graph, dump_pcb_graph

# Load existing KiCad PCB into graph representation
graph_data = load_pcb_graph(Path("design.kicad_pcb"))
pcb_node = graph_data.pcb_node

# Manipulate graph (e.g., modify trace widths)
for line in pcb_node.get_children(direct_only=True, types=LineNode):
    if get_net_id(line) == target_net:
        line.width.alias_is(new_width)

# Export back to KiCad format
output_content = dump_pcb_graph(graph_data, Path("modified.kicad_pcb"))
```

The construction patterns emphasize parameter preservation and symbolic relationships to support future solver integration.

### Zone Geometry Node Responsibilities

We normalise zone geometry into a four-layer hierarchy so topology, semantics, and literal coordinates stay cleanly separated while still round-tripping KiCad’s polygon structures. Each layer carries specific responsibilities:

- **ZoneNode** (one per KiCad `zone` stanza)

  - _Ownership_: acts as the semantic envelope, linking to the electrical net, active layer stack, and zone-wide settings (clearance, fill enable/mode, hatch strategy, thermal/teardrop overrides, keepout rules, netclass references).
  - _Metadata_: preserves zone-level UUIDs, names, priority, KiCad attribute payloads (keepout tables, placement constraints, rule overrides) via backend-specific child parameters so exporters can faithfully restore the stanza.
  - _Geometry registry_: keeps ordered references to child `PolygonNode`s—exactly one marked as the primary outline, zero-or-more holes, and optional filled-area polygons that KiCad emits after a zone fill.
  - _Connectivity_: connects to the owning `NetNode` (when copper-bearing) plus relevant stackup/layer descriptors so downstream passes can reason about electrical scope.

- **PolygonNode** (one per contiguous loop: outline, hole, or filled island)

  - _Role markers_: records whether the loop is an outline, internal void, or post-fill island via parameters like `polygon_role`.
  - _Provenance_: stores the polygon UUID and raw KiCad sub-structures (`polygon`, `filled_polygon`, etc.) as passthrough parameters for lossless export.
  - _Geometry children_: contains `XYRNode` children for straight line segments and `ArcNode` children for curved segments, connected in sequence to form the polygon outline.
  - _Layer information_: stores layer names and other polygon-specific metadata as parameters.

- **XYRNode & ArcNode** (reused geometry primitives)
  - _XYRNode_: represents individual points in the polygon with `x`, `y` coordinates and optional `r` rotation.
  - _ArcNode_: represents curved segments with `start`, `center`, `end` coordinates and `width` (typically 0 for polygon outlines).
  - _Connectivity_: connected in sequence to form the polygon ring, with optional connections to related geometry.

This approach reuses existing geometry node types rather than creating polygon-specific variants, keeping the overall node type count manageable while still supporting complex polygon shapes with both straight and curved segments.

## Import / Export Process

1. **Load (KiCad → Graph)**

   - Parse `.kicad_pcb` using the existing dataclasses (`C_kicad_pcb_file`). # ideally we go straight from kicad_pcb -> Graph
   - Walk the dataclass tree, instantiating graph nodes with helper builders:
     1. Create the `PCBNode` root, populate board/setup metadata, layer stack, and UUID registry.
     2. Emit `NetNode`s for every KiCad net and attach global rule nodes (net classes, design rules).
     3. For each footprint, instantiate a `FootprintNode`, attach pose + properties, then create child pads, text, graphics, and 3D model nodes while wiring them to the relevant nets/layers.
     4. Import free geometry (segments, zones, keepouts) and board outlines, linking them to stackup/layer nodes and associated nets.
   - Maintain maps (UUID → node) to support incremental updates and deduplicate shared objects (e.g. multiple pads referencing one net).

2. **Transform (Graph Mutations)**

   - After load, the graph is amenable to solver passes, DRC checks, or user edits through Faebryk traits. Parameters may remain symbolic during this phase. # Wont do for now

3. **Dump (Graph → KiCad)**
   - Traverse the graph deterministically, regenerating KiCad dataclasses: # ideally we go straight from graph -> PCB if possible
     1. Rebuild the layer table and stackup based on `LayerNode` and stackup descriptors.
     2. Emit nets, assigning IDs from `NetNode` literals (or generating new IDs if absent).
     3. For each footprint, write placement, properties, text, pads (including per-layer options), and reattach original UUIDs.
     4. Serialize board-level primitives (tracks, vias, zones, outlines) using helper functions akin to `transformer.py`.
   - Finally, write the dataclass tree back to disk (or in-memory buffer) via `dumps`, preserving formatting and UUID stability.

This pipeline should mirror the existing transformer flow so we can adopt it incrementally: first load and immediately dump to validate parity, then introduce mutations/tests.

## Current Implementation Status

### Completed Components

- **Core Graph Infrastructure**: All base node types with proper `d_field` declarations
- **Primitive Geometry Nodes**: `LineNode`, `ArcNode`, `CircleNode`, `RectangleNode`, `ViaNode` with full parameter support
- **Layer System**: `LayerNode` + `KicadLayerNode` for backend-agnostic layer representation
- **Net Management**: `NetNode` with connectivity and ID management
- **Polygon Support**: `PolygonNode` with `XYRNode` and `ArcNode` children for points and arc segments
- **Footprint Hierarchy**: `FootprintNode`, `PadNode`, `TextNode`, `FootprintPropertyNode` with pose management
- **Zone Support**: `ZoneNode` + `ZoneSettingsNode` with polygon-based geometry
- **Import/Export Pipeline**: Full KiCad PCB roundtrip via `load_pcb_graph()` and `dump_pcb_graph()`
- **Parameter Preservation**: Symbolic parameter handling with `alias_is()` for solver compatibility

### In Progress / Refinements Needed

- **Via Pad Geometry**: Simplified via representation (removed complex pad_front/pad_back for now)
- **Zone Filled Polygons**: Basic support implemented, may need optimization for large zones
- **Type Safety**: Some Parameter alias type mismatches need resolution
- **Line Length**: Code formatting cleanup needed in transformer

### Not Yet Implemented

- **Net Classes & Design Rules**: `NetClassNode` and `RuleNode` defined but not integrated
- **Groups & Hierarchy**: `GroupNode` defined but import/export not wired up
- **Board Setup Details**: Advanced teardrops, plot parameters stored as raw passthrough
- **3D Models**: Footprint 3D model references stored in raw footprint data
- **Advanced Text Effects**: Complex text styling stored as KiCad-specific parameters
- **Keepout Zones**: Basic zone support exists, keepout-specific logic needs refinement

### Architecture Decisions Made

- **Hybrid Approach**: Core geometry and connectivity fully graph-based; complex KiCad-specific metadata stored as parameters for now
- **Parameter-First Design**: All numeric values stored as `Parameter` nodes to support future solver integration
- **Layered Abstraction**: `KicadLayerNode` children provide backend-specific data while keeping `LayerNode` generic
- **Polygon Simplification**: Direct use of `XYRNode` and `ArcNode` children avoids unnecessary hierarchy while supporting complex arc-based outlines
- **Conservative Roundtrip**: Preserve all KiCad metadata during import/export to ensure zero data loss
- **Flexible Rules System**: Design rules can be attached at multiple levels (board-wide manufacturing constraints, net-specific width requirements, spacing rules) using `RuleNode` instances
- **Clean Core Schema**: KiCad-specific metadata (UUIDs, library references) attached via dedicated child nodes rather than polluting core node interfaces
- **Permissive Properties**: User-defined properties support arbitrary key/value pairs to match KiCad's flexibility
- **Geometric Board Outline**: Board edges represented as dedicated node with primitive children rather than layer-tagged segments

### Future Refactoring Opportunities

- **Footprint Graphics**: Decompose `raw_footprint` passthrough into explicit `LineNode`/`ArcNode` children
- **Advanced Zones**: Separate keepout rules, thermal settings, and fill algorithms into dedicated node types
- **Pad Stacks**: Model complex pad geometries (castellated, plated slots) as structured child nodes
- **Design Rules**: Integrate `NetClassNode` and `RuleNode` into the import/export pipeline
- **Change Tracking**: Add graph-based diff/merge capabilities for version control workflows

## Delivery Status

### ✅ Completed

1. **Node Schemas**: All core primitive and metadata node types defined with proper `d_field` declarations
2. **KiCad Importer**: `load_pcb_graph()` function traverses KiCad dataclasses and creates graph nodes
3. **KiCad Exporter**: `dump_pcb_graph()` function reads graph and emits KiCad dataclasses with full fidelity
4. **Helper Functions**: Construction utilities (`new_line`, `new_arc`, etc.) for ergonomic primitive creation

### 🔄 In Progress

1. **Type Safety**: Resolving Parameter alias type mismatches in transformer
2. **Code Quality**: Linting cleanup and line length fixes
3. **Via Geometry**: Simplified via model may need refinement for complex pad stacks

### 📋 Future Work

1. **Regression Tests**: Comprehensive test suite using `esp32_minimal` and other fixtures
2. **Integration**: Wire up `NetClassNode`, `GroupNode`, and `RuleNode` to import/export
3. **Performance**: Optimize polygon handling for very large zones
4. **Documentation**: API documentation and usage examples
5. **Board Outline Node**: Dedicated node for board edges with primitive children (lines/arcs) for mechanical boundaries
6. **Design Metadata Node**: Top-level container for paper size, title block, project name, and other file-level metadata
7. **Advanced Design Rules**: Differential pair rules, teardrop options, solder mask clearances as structured rule nodes
