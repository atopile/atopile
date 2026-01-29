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

## Relation to Python fileformats

- `src/faebryk/libs/kicad/fileformats.py` defines Python dataclasses for KiCad JSON artifacts (e.g., DRC reports, project files). The Zig layer targets KiCad’s S‑expression text formats and is accessed from Python via `faebryk.core.zig`.

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
