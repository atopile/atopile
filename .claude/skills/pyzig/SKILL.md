---
name: Pyzig
description: "How the Zig↔Python binding layer works (pyzig), including build-on-import, wrapper generation patterns, ownership rules, and where to add new exported APIs."
---

# Pyzig Module

`pyzig` is the Zig↔Python interoperability layer used by Faebryk’s native modules (graph, sexp, faebryk typegraph, …).

There are three distinct layers to keep straight:
- **Python loader/glue**: `src/faebryk/core/zig/__init__.py` (build-on-import + `.pyi` syncing)
- **Zig build**: `src/faebryk/core/zig/build.zig` (builds `pyzig.so` + `pyzig_sexp.so`, generates stubs)
- **Zig binding utilities**: `src/faebryk/core/zig/src/pyzig/*` (wrapper generation + minimal C-API surface)

## Quick Start

```bash
ato dev compile
python -c "import faebryk.core.zig; import faebryk.core.graph"
```

## Relevant Files

- Python-side loader/build glue:
  - `src/faebryk/core/zig/__init__.py` (`ZIG_NORECOMPILE`, `ZIG_RELEASEMODE`, lock, stub syncing)
- Zig build + stub generation:
  - `src/faebryk/core/zig/build.zig` (builds extensions + runs `.pyi` generator)
- Core pyzig utilities:
  - `src/faebryk/core/zig/src/pyzig/pybindings.zig` (minimal CPython C-API declarations)
  - `src/faebryk/core/zig/src/pyzig/pyzig.zig` (wrapper generation helpers)
  - `src/faebryk/core/zig/src/pyzig/type_registry.zig` (global type-object registry)
  - `src/faebryk/core/zig/src/pyzig/pyi.zig` (stub generation helpers)
- Example consumers:
  - `src/faebryk/core/zig/src/python/graph/graph_py.zig`
  - `src/faebryk/core/zig/src/python/sexp/sexp_py.zig`

## Dependants (Call Sites)

- Graph bindings: `src/faebryk/core/zig/src/python/graph/*`
- Sexp bindings: `src/faebryk/core/zig/src/python/sexp/*`
- TypeGraph bindings: `src/faebryk/core/zig/src/python/faebryk/*` (and friends)

## How to Work With / Develop / Test

### Core Concepts
- **Direct binding**: pyzig calls the CPython C-API directly (no cffi/ctypes).
- **Wrapper types**: most exposed Zig structs become Python heap types via `wrap_in_python(...)` / `wrap_in_python_simple(...)`.
- **Global type registry**: prevents re-creating Python `PyTypeObject`s for the same Zig type (`type_registry`).
- **No direct `__init__` (by default)**: many “reference” types are not meant to be user-constructed; `pyzig` often installs an init that raises.
- **Debug handle**: generated wrappers include `__zig_address__()` to help debug pointer identity.

### Development Workflow
1) Edit Zig:
   - binding helpers: `src/faebryk/core/zig/src/pyzig/*`
   - module wrappers: `src/faebryk/core/zig/src/python/**`
2) Rebuild native modules:
   - `ato dev compile` (imports `faebryk.core.zig`; editable installs compile-on-import)
   - set `ZIG_RELEASEMODE=ReleaseFast|ReleaseSafe|Debug` as needed
3) If you changed stubs/output:
   - ensure `src/faebryk/core/zig/gen/**` gets updated (this is driven by `src/faebryk/core/zig/__init__.py`)

### Testing
- Smoke tests are usually through downstream modules:
  - `python -m faebryk.core.graph` (GraphView allocation/cleanup stress)
  - `pytest test/core/solver` (heavy user of graph + bindings via many subsystems)

## Best Practices
- **Assume mistakes segfault**: treat changes here like unsafe systems programming.
- **Be explicit about ownership**:
  - if a wrapper allocates Zig memory, define how it is freed (explicit `.destroy()` vs `tp_dealloc` calling `.deinit()`).
  - if you duplicate input buffers (sexp does), expose a `free(...)` path and document it.
- **Don’t rely on Python GC for Zig arenas** unless you intentionally installed a `tp_dealloc` that calls `deinit`.
- **Stub hygiene matters**: keep the `.pyi` surface accurate; many callers rely on types for navigation.

## Build-on-import behavior (important)

`src/faebryk/core/zig/__init__.py` is responsible for:
- compiling extensions in editable installs (unless `ZIG_NORECOMPILE=1`)
- loading `pyzig.so` and `pyzig_sexp.so` from `src/faebryk/core/zig/zig-out/lib/`
- copying + formatting generated `.pyi` files into `src/faebryk/core/zig/gen/**` (black + ruff)
