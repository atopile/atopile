---
name: Sexp
description: "How the Zig S-expression engine and typed KiCad models work, how they are exposed to Python (pyzig_sexp), and the invariants around parsing, formatting, and freeing."
---

# Sexp Module

The sexp subsystem provides:
- a fast S-expression tokenizer/parser/pretty-printer in Zig, and
- typed Zig models for KiCad formats (PCB, footprint, netlist, symbol, schematic, fp_lib_table),
exposed to Python via the `pyzig_sexp` extension module.

Source-of-truth docs and code:
- `src/faebryk/core/zig/README.md` (high-level overview)
- `src/faebryk/core/zig/src/sexp/*` (tokenizer/AST/structure)
- `src/faebryk/core/zig/src/python/sexp/sexp_py.zig` (Python API + critical memory rules)

## Quick Start

```python
from pathlib import Path
from faebryk.libs.kicad.fileformats import kicad

pcb = kicad.loads(kicad.pcb.PcbFile, Path("board.kicad_pcb"))
_text = kicad.dumps(pcb)
```

## Relevant Files

- Zig core:
  - `src/faebryk/core/zig/src/sexp/tokenizer.zig` (tokenization + line/column tracking)
  - `src/faebryk/core/zig/src/sexp/ast.zig` (SExp tree + KiCad pretty formatting)
  - `src/faebryk/core/zig/src/sexp/structure.zig` (decode/encode + error context)
  - `src/faebryk/core/zig/src/sexp/kicad/*` (typed KiCad models)
- Python extension entrypoint:
  - `src/faebryk/core/zig/src/python/sexp/init.zig` (exports `PyInit_pyzig_sexp`)
  - `src/faebryk/core/zig/src/python/sexp/sexp_py.zig` (module + type binding generation)
- Generated Python stubs (what users “see”):
  - `src/faebryk/core/zig/gen/sexp/*.pyi`
- Convenience wrapper used throughout the codebase:
  - `src/faebryk/libs/kicad/fileformats.py` (namespaces modules + caching + `loads/dumps`)

## Dependants (Call Sites)

- `src/faebryk/libs/kicad/fileformats.py` (primary integration layer)
- KiCad exporters and layout sync:
  - `src/faebryk/exporters/pcb/kicad/*`
  - `src/faebryk/exporters/pcb/layout/layout_sync.py`
- KiCad plugin workflow: `src/atopile/kicad_plugin/*`

## How to Work With / Develop / Test

### Core Concepts
- **Two-level model**:
  - raw `SExp` parsing/formatting (`tokenizer.zig`, `ast.zig`)
  - typed KiCad decoding/encoding (`structure.zig` + `sexp/kicad/*.zig`)
- **Python API shape**: the extension exposes per-format modules (e.g. `pcb`, `netlist`) with:
  - module-level `loads(data: str) -> File`
  - module-level `dumps(file: File) -> str`
  - `File.free(...)` for releasing Zig-owned allocations
- **Convenience wrapper**: `faebryk.libs.kicad.fileformats.kicad` wraps these modules and provides `kicad.loads(...)`/`kicad.dumps(...)`.

### Development Workflow
1) Modify Zig:
   - parsing/formatting: `src/faebryk/core/zig/src/sexp/*`
   - Python exposure: `src/faebryk/core/zig/src/python/sexp/sexp_py.zig`
2) Rebuild:
   - `ato dev compile` (imports `faebryk.core.zig`)
3) If you changed the API:
   - verify stubs under `src/faebryk/core/zig/gen/sexp/*.pyi` update accordingly
   - adjust `src/faebryk/libs/kicad/fileformats.py` if needed

### Testing
- Best practical test is round-trip:
  - load a known `.kicad_pcb` / `.kicad_sch`, dump it, and ensure KiCad accepts it (formatting-sensitive).
- Zig unit tests (where present):
  - `zig test src/faebryk/core/zig/src/sexp/ast.zig`
  - `zig test src/faebryk/core/zig/src/sexp/structure.zig`

## Best Practices
- Prefer `faebryk.libs.kicad.fileformats.kicad` unless you explicitly need the raw module API.
- Be mindful of **shared-object caching** in `kicad.loads(...)`: path-based loads are cached and returned by reference (mutations are shared).

## Memory & Lifetime Invariants (critical)

The Python bindings duplicate the input S-expression string into a persistent allocator because parsed structs contain pointers into the input buffer.

Implications:
- Repeated `loads(...)` of large files can grow memory if you never call `free(...)` on the returned `*File`.
- The convenience wrapper currently caches loaded objects by path; do not `free(...)` cached objects unless you also invalidate the cache.
