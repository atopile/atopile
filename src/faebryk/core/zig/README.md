# Zig S‑Expressions + Python Bindings (KiCad)

## Overview

- Implements a fast S‑expression engine in Zig and typed KiCad file models (PCB, footprint, netlist, symbol, schematic, fp_lib_table).
- Exposes Zig types and I/O helpers to Python as a compiled extension module `pyzig` with generated `.pyi` stubs.
- Focuses on round‑tripping KiCad’s text formats with correct formatting and helpful error context.

## Layout

- `src/sexp` — S‑expression core and KiCad schemas
  - `tokenizer.zig` — High‑throughput tokenizer with location tracking.
  - `ast.zig` — SExp tree, parser, pretty printer (KiCad‑compatible layout), helpers.
  - `structure.zig` — Generic decode/encode using Zig type introspection + per‑field metadata; error context capture and free helpers.
  - `kicad/*.zig` — Typed models for KiCad files, each with `File` wrapper exposing `loads/dumps/free`:
    - `pcb.zig`, `footprint.zig`, `netlist.zig`, `symbol.zig`, `schematic.zig`, `fp_lib_table.zig`.
    - Versioned variants under `kicad/v5` and `kicad/v6` where needed.
  - `py.zig` — Builds the `pyzig` Python extension and submodules (pcb, footprint, …), wiring loads/dumps to Python.
  - `pyi.zig` — Generates `.pyi` stubs for all submodules at build time.
- `src/pyzig` — Python interop scaffolding
  - `pybindings.zig` — Minimal Python C‑API surface (types, refcount ops, lists, errors…).
  - `pyzig.zig` — Utilities to wrap Zig structs as Python types (getters/setters for ints/enums/strings/optionals/structs, repr, type registry).
  - `linked_list.zig` — Python-compatible wrapper over `std.DoublyLinkedList(T)` with sequence protocol and list methods.
- Top‑level build + Python glue
  - `build.zig` — Builds static lib `sexp`, Python extension `pyzig`, and runs the `pyi` generator.
  - `__init__.py` — On editable installs: compiles `pyzig` with the running interpreter and copies/ruff‑formats generated `.pyi` files.

## Python API (quick start)

- Import modules from the built extension:
  - `from faebryk.core.zig import pcb, footprint, netlist, symbol, schematic, fp_lib_table`
- Parse/dump KiCad S‑expression files:
  - `pcb_file = pcb.loads(path_or_text)`
  - `text = pcb.dumps(pcb_file)`
- Objects exposed to Python are thin wrappers over Zig structs. Lists from Zig are `pyzig.MutableList` (backed by Zig `std.DoublyLinkedList` for memory stability), supporting `len()`, index, `append/pop/insert/clear`, `in`, and iteration.

## S‑expression engine (key points)

- Tokenizer and Parser
  - Produces `SExp` tree with precise `line/column` locations for all tokens.
  - Duplicates token text into allocator‑owned memory to avoid use‑after‑free.
- Pretty printer
  - `SExp.pretty(allocator)` renders with KiCad’s spacing and newline rules, including special handling for `xy` lists and “short‑form” constructs (font/stroke/fill/etc.).
- Generic decode/encode
  - `structure.decode/encode` map S‑expressions to Zig structs using compile‑time reflection and per‑field `fields_meta`:
    - `positional` ordering, `multidict` collection (repeated keys), `sexp_name` overrides, `order`, `symbol` string‑as‑symbol, boolean encodings (symbol vs. parentheses).
  - Rich `ErrorContext` threads through decoding for actionable Python exceptions (type, field, preview, location).
  - `structure.free` frees decoded data recursively.

## KiCad models

- Each file type provides a `File` wrapper with:
  - `loads(allocator, input)` — parse from path/string/sexp; validates the top‑level symbol.
  - `dumps(allocator, output)` — serialize to string or path with KiCad‑style formatting.
  - `free(allocator)` — release allocated memory.
- See the generated stubs in this folder: `pcb.pyi`, `footprint.pyi`, `netlist.pyi`, `symbol.pyi`, `schematic.pyi`, `fp_lib_table.pyi`, plus versioned `*_v5.pyi`/`*_v6.pyi`.

## Python bindings details

- Types are exposed via `src/sexp/py.zig` using helpers from `src/pyzig/pyzig.zig`.
  - Property helpers for ints/floats/bools/strings/enums/optionals and nested struct fields.
  - `MutableList(T)` wraps a `std.DoublyLinkedList(T)` to provide a memory-stable Python list interface with common list methods.
  - A global type‑object registry avoids re‑creating Python types for the same Zig struct.
- Stubs: `src/sexp/pyi.zig` + `src/pyzig/pyi.zig` generate `.pyi` files so IDEs and type checkers understand the exposed APIs.

## Build and import

- Editable installs auto‑build on import. `src/faebryk/core/zig/__init__.py`:
  - Invokes `python -m ziglang build python-ext` with the current interpreter’s include/lib paths.
  - Copies formatted `.pyi` outputs from `zig-out/lib/*.pyi` into this folder.
- Manual: `zig build python-ext -Doptimize=ReleaseSafe -Dpython-include=... [-Dpython-lib=... -Dpython-lib-dir=...]`.

## Memory Management

### Zig-Python Memory Model
- Parser duplicates token text into allocator-owned memory
- Python `loads()` duplicates input strings to keep pointers valid after returning to Python
- File wrappers have `free(allocator)`; Python wrappers retain data for process lifetime
- Two construction patterns: `zig::loads()` (Zig owns) vs generated constructors (Python owns)

### Critical: Defer Ordering
**Zig `defer` executes LIFO (Last In, First Out)** — containers must be cleaned up before their children:

```zig
var graph = GraphView.init(allocator);
const node1 = try Node.init(allocator);
defer _ = node1.deinit() catch {};  // Runs 2nd
defer graph.deinit();               // Runs 1st ← Graph cleanup BEFORE nodes
```

**Rule:** Place `defer` for parents **after** children are created, so cleanup happens in reverse dependency order.

### Ownership & Shallow Copies
Zig performs shallow copies (bitwise copy of struct fields, not heap data). For `ArrayList`-like structs:
- Only metadata (~24 bytes) is copied
- Both copies point to same heap allocation
- **Single deinit rule:** Only one owner calls `.deinit()`
- Use `var mutable = param` to get mutable binding for cleanup

**BFS Example:**
```zig
var path = queue.orderedRemove(0);  // Ownership transfer
visitor_fn(ctx, path);              // Another shallow copy
if (!keep_path) {
    var mutable = path;             // Need mutable for deinit
    mutable.deinit();
}
```

## Graph Pathfinder

The pathfinder implements a filtered BFS algorithm to find valid connection paths through the component hierarchy graph.

### Graph Structure
- **`EdgeComposition`** — Parent/child hierarchy relationships (Module contains Interfaces)
- **`EdgeInterfaceConnection`** — Electrical/logical connections between interfaces
- **Directions**: UP (child→parent), DOWN (parent→child), HORIZONTAL (interface connections)

### Path Filters
1. **`count_paths`** — Safety limits (stops at 1M paths)
2. **`filter_only_end_nodes`** — Only keep paths ending at target nodes
3. **`filter_path_by_edge_type`** — Require paths to start and end on composition or interface connection edges
4. **`filter_siblings`** — Reject child→parent→child through same parent (sibling jumps)
5. **`filter_hierarchy_stack`** — **Critical filter** ensuring valid hierarchy traversal

### Hierarchy Rules

**Rule 1: Balanced traversal** — Paths must return to start hierarchy level
- DOWN (parent→child): Push onto stack
- UP (child→parent): Pop matching element from stack
- Valid: Stack empty at end

**Rule 2: No descent before ascent** — Cannot descend from starting level
- Empty stack + DOWN edge → **Reject immediately**

**Rule 3: Shallow link restrictions** — Shallow links only accessible from same/higher level
- Track depth: starts at 0, UP+1, DOWN-1
- Shallow link at depth > 0 → **Reject** (starting node is lower than link)

**Example:**
```
Parent (EP_1)          AnotherParent (EP_2)
  ├─ Child (LV_1)        ├─ Child (LV_2)  
  └─ Child (HV_1)        └─ Child (HV_2)
```

✅ Valid: `LV_1 → EP_1 → EP_2 → LV_2` (UP then DOWN)  
❌ Invalid: `EP_1 → LV_1` (DOWN from start)  
❌ Invalid: `LV_1 → LV_2` without UP first

**Key insight:** Valid connections go "up-then-across-then-down" through hierarchy. Shallow links prevent child components from accessing parent-level connections they shouldn't see.

### Conditional Edge System

Allows certain paths to be marked as "weak" and overridden by "strong" paths, enabling direct connections to take precedence over sibling connections.

#### Core Concepts

**1. Path Tracking** — Paths remember if they use conditional edges:
```zig
pub const BFSPath = struct {
    via_conditional: bool = false,  // Uses conditional edges?
};
```

**2. Smart Visited Tracking** — Nodes remember HOW they were reached:
```zig
pub const VisitInfo = struct {
    via_conditional: bool,  // Previously visited via conditional path?
};
```

**3. Override Logic** — Strong paths can override weak paths:
```zig
// Can revisit if: previous=conditional AND current=non-conditional
const can_revisit = visit_info.via_conditional and !self.current_path_via_conditional;
return !can_revisit; // Skip if we can't revisit
```

**4. Cycle Detection** — Prevents infinite loops:
```zig
// Never revisit nodes already in current path
for (self.current_path.path.edges.items) |path_edge| {
    if (Node.is_same(path_edge.source, other_node.?) or Node.is_same(path_edge.target, other_node.?)) {
        return SKIP; // Would create cycle
    }
}
```

#### Use Cases

- **Sibling vs Direct**: `A → Parent → B` (conditional) vs `A → B` (non-conditional) → Direct wins
- **Shallow Links**: Regular connections override shallow connections when both available  
- **Extensible**: Add new edge attributes (`"conditional"`, `"weak"`, `"temporary"`) with same override logic

#### Implementation
- **Memory**: `VisitInfo` in `NodeRefMap.T(VisitInfo)` for O(1) lookup
- **Performance**: Minimal overhead (one boolean per path)
- **Debugging**: Set `DEBUG = true` in `graph.zig` and `pathfinder.zig` for detailed BFS output

## Relation to Python fileformats

- `src/faebryk/libs/kicad/fileformats.py` defines Python dataclasses for KiCad JSON artifacts (e.g., DRC reports, project files). The Zig layer targets KiCad's S‑expression text formats and is accessed from Python via `faebryk.core.zig`.

## Developing and tests

- Notes and open items: `src/faebryk/core/zig/INTEGRATION.md`, `TESTS.md`, `TODO.md`.
- Zig tests and perf scaffolding exist in `build.zig` but are not enabled by default; KiCad behavior is primarily validated via the Python test suite.

## File Pointers

- `src/faebryk/core/zig/build.zig:1`
- `src/faebryk/core/zig/__init__.py:1`
- `src/faebryk/core/zig/src/sexp/structure.zig:1`
- `src/faebryk/core/zig/src/sexp/ast.zig:1`
- `src/faebryk/core/zig/src/sexp/tokenizer.zig:1`
- `src/faebryk/core/zig/src/sexp/kicad/pcb.zig:1`
- `src/faebryk/core/zig/src/sexp/py.zig:1`
- `src/faebryk/core/zig/src/pyzig/pyzig.zig:1`
- `src/faebryk/core/zig/src/pyzig/linked_list.zig:1`
