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

## Memory and lifetimes

- The parser duplicates token text; higher‑level `loads` for Python duplicates the input string into the C allocator to keep pointers valid after returning to Python.
- File wrappers have `free(allocator)`; Python wrappers currently retain data for process lifetime unless explicitly freed from Zig. Avoid holding onto many large parsed files at once.

Currently two ways of constructing structured sexp objects (e.g pcb).

- zig::loads:
  - zig will allocate and own memory for the structs
  - if python gets an object it will run through obj prop which will allocate a pyobj wrapper that contains a pointer to the zig struct
- generated python constructor
  - since we generate a constructor for each struct (generated_init), python will allocate the memory the pyobj wrapper, onto which we then allocate a new zig struct and store the pointer in the pyobj wrapper

### Defer and cleanup ordering (critical!)

**Zig's `defer` statements execute in LIFO (Last In, First Out) order** — like a stack, the last defer added runs first.

This matters when you have dependencies between resources:

```zig
var graph = GraphView.init(allocator);
const node1 = try Node.init(allocator);
defer _ = node1.deinit() catch {};  // Runs 2nd
const node2 = try Node.init(allocator);
defer _ = node2.deinit() catch {};  // Runs 3rd
defer graph.deinit();               // Runs 1st ← MUST clean up graph BEFORE nodes
```

**Why:** If nodes are inserted into the graph, the graph holds references to them. You must:
1. Clean up the parent/container first (releases references)
2. Then clean up the children/contained objects

**Wrong order causes memory leaks** because child `.deinit()` will fail with `error.InUse` when the reference count is still > 0.

**Rule of thumb:** Place `defer` for containers/parents **after** all their children are created, so cleanup happens in reverse dependency order.

### Ownership patterns and shallow copies

**Zig doesn't have automatic move semantics like Rust.** When you pass a struct by value, Zig performs a shallow copy (bitwise copy of the struct fields).

For structs that wrap heap allocations (like `ArrayList`), this means:
- The struct metadata (~24 bytes: pointer + length + capacity) is copied
- The underlying heap data is NOT copied
- Both copies point to the same heap allocation

**Key implications:**
1. **Ownership transfer via shallow copy:** When you `append(path)` to an ArrayList or pass a struct by value, you're creating a new owner of the same heap data
2. **Single deinit rule:** Only ONE owner should call `.deinit()` on the struct, otherwise you'll free the same memory twice
3. **Function parameters are immutable:** Even when passed by value, you need `var mutable = param` to get a mutable binding to call `.deinit()`

**Example - BFS path handling:**
```zig
// Queue stores Path values for cache locality
var open_path_queue = std.ArrayList(Path).init(allocator);

// Pop transfers ownership (shallow copy from queue to local variable)
var path = open_path_queue.orderedRemove(0);

// Visitor receives ownership (another shallow copy)
visitor_fn(ctx, path);  // fn(ctx, Path)

// Inside visitor:
if (keep_path) {
    // Move into results (shallow copy, transfers ownership)
    self.path_list.?.append(path) catch |err| { ... };
} else {
    // Discard - need mutable binding to call deinit
    var mutable_path = path;
    mutable_path.deinit();
}
```

**Memory locality vs pointer indirection:**
- `ArrayList(Path)` — Paths stored contiguously → better cache performance during iteration
- `ArrayList(*Path)` — Paths scattered in heap → pointer chasing, worse cache
- For hot paths like BFS, prefer value storage even with shallow copy overhead (~24 byte copies)

## Graph Pathfinder

The pathfinder (`src/faebryk/core/zig/src/faebryk/pathfinder.zig`) implements a filtered BFS algorithm to find valid connection paths through the component hierarchy graph.

### Graph Structure

The graph consists of two edge types:
- **`EdgeComposition`** — Parent/child hierarchy relationships (e.g., a Module contains Interfaces)
- **`EdgeInterfaceConnection`** — Actual electrical/logical connections between interfaces

Each composition edge has a direction:
- **UP** — Traversing from child to parent
- **DOWN** — Traversing from parent to child
- **HORIZONTAL** — Interface connections (same hierarchy level)

### Path Filters

The pathfinder runs a series of filters on each path during BFS traversal:

1. **`count_paths`** — Statistics and safety limits (stops at 1M paths)
2. **`filter_only_end_nodes`** — If target nodes specified, only keep paths ending at targets
3. **`filter_path_by_edge_type`** — Only allow `EdgeComposition` and `EdgeInterfaceConnection` edges
4. **`filter_path_by_node_type`** — (Future) type compatibility checking
5. **`filter_siblings`** — Reject paths with child→parent→child through same parent (sibling jumps)
6. **`filter_heirarchy_stack`** — **The critical filter** ensuring valid hierarchy traversal

### Hierarchy Stack Filter (Key Logic)

This filter maintains a stack of hierarchy elements to enforce three rules:

#### Rule 1: Balanced hierarchy traversal
Paths must return to the same hierarchy level as the start node. The stack tracks each UP/DOWN traversal:
- **DOWN movement** (parent→child): Push element onto stack
- **UP movement** (child→parent) that matches the top: Pop from stack
- **Valid path**: Stack is empty at the end (returned to start level)

#### Rule 2: No descent before ascent
**Paths cannot descend into children from the starting hierarchy level.**

When the stack is empty (we're at the starting level) and we encounter a DOWN edge:
→ **Reject the path immediately**

#### Rule 3: Shallow link restrictions
**Shallow links can only be crossed if the starting node is at the same hierarchical level or higher than where the shallow link is located.**

Shallow links are special `EdgeInterfaceConnection` edges marked with `shallow_link = true`. These represent connections that should only be accessible if you start from the same level or above (closer to root):
- Track hierarchy depth as we traverse: starts at 0, UP increments (+1), DOWN decrements (-1)
- When encountering a shallow link, check if `depth <= 0`
- If `depth > 0` (we've ascended above start), the starting node is **lower** than the link → reject
- If `depth <= 0` (at or below start), the starting node is at same/higher level than the link → allow

**Why this matters:**

```
Parent (EP_1)
  ├─ Child (LV_1)  
  └─ Child (HV_1)

AnotherParent (EP_2)
  ├─ Child (LV_2)
  └─ Child (HV_2)
```

Without Rule 2:
- ❌ `EP_1 → LV_1` would be valid (direct parent-to-child)
- ❌ `LV_1 → EP_1 → LV_2` would have balanced stack but wrong semantics

With Rule 2:
- ✅ `EP_1 → EP_1` (self-connection, empty path)
- ✅ `EP_1 → EP_2` (horizontal connection)
- ✅ `LV_1 → EP_1 → EP_2 → LV_2` (UP then DOWN, valid connection through hierarchy)
- ✅ `HV_1 → EP_1 → EP_2 → HV_2` (children connect via their parents)
- ❌ `EP_1 → LV_1` (DOWN from start, rejected)
- ❌ `LV_1 → LV_2` if only connected via `EP_1 → EP_2` (requires UP first)

With Rule 3 (Shallow Links):
```
Root
  ├─ Module (M1)
  │    ├─ SubModule (S1)
  │    │    └─ Interface (I1)
  │    └─ Interface (Shallow_I)  ← shallow link defined here
  └─ Module (M2)
       └─ Interface (I2)
```

If `Shallow_I ←→ I2` (shallow interface connection):
- ✅ Starting from **M1**: `M1 → Shallow_I → I2` (depth = 0 at shallow link, M1 is same level as link)
- ✅ Starting from **Root**: `Root → M1 → Shallow_I → I2` (depth = -1 at shallow link, Root is higher than link)
- ❌ Starting from **S1**: `S1 → M1 → Shallow_I → I2` (depth = +1 at shallow link, S1 is lower than link)
- ❌ Starting from **I1**: `I1 → S1 → M1 → Shallow_I → I2` (depth = +2 at shallow link, I1 is lower than link)

The rule prevents child components from using shallow links defined at parent levels. Shallow links are "shallow" because they're only visible from the same level or above where they're defined, not from deeper child components.

**The insight:** Valid connections must go "up-then-across-then-down" through the hierarchy. Starting with a descent means you're trying to connect to your own children without an actual interface connection. Shallow links enforce an additional constraint: they can only be used if you start from the same hierarchical level or higher (closer to root) than where the link is defined. This prevents child components from reaching "up and across" to use parent-level connections they shouldn't have access to.

This elegantly prevents direct connections through composition edges while allowing legitimate hierarchical connections where children connect via their parents, with shallow links providing fine-grained control over connection visibility.

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
