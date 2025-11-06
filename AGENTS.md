# 0.14 Staging branch

This release will contain deep core changes. 
Primarily using zig and the new graph language.
Also restructuring of what faebryk means.

Primary goals:
- speed
- maintainability
- understanding of the core
- more powerful graph
- serializable graph

## Zig-Python Architecture

### Overview
Core performance-critical functionality is implemented in Zig (`src/faebryk/core/zig/src/`). Python bindings expose this via the `pyzig` binding layer in `src/faebryk/core/zig/src/python/`.

### File Structure
- `src/faebryk/core/zig/src/` - Core Zig implementations (graph, interfaces, algorithms)
- `src/faebryk/core/zig/src/python/*_py.zig` - Python wrappers for Zig types/functions
- `src/faebryk/core/zig/src/python/*/manual/*.pyi` - Type stubs for IDE support
- `src/faebryk/core/zig/src/pyzig/` - Generic Python-Zig binding utilities

### Data Flow
Python call → Python wrapper (Zig) parses args → Core Zig function → Wrapper converts result → Python receives native types

### Memory Management
1. **Zig-owned**: Allocated with Zig allocator, must call `deinit()` when done
2. **Python-owned wrappers**: Thin Python objects wrapping Zig data, custom deallocators call `deinit()` on GC
3. **Ownership transfer**: Zig allocates → wraps in Python object → Python GC handles cleanup

### Adding Python-Accessible Functions
1. Implement function in Zig (e.g., in `graph.zig` or `interface.zig`)
2. Create wrapper in corresponding `*_py.zig` file using `wrap_*` pattern
3. Add wrapper to appropriate `extra_methods` array
4. Update type stub in `manual/*.pyi` file

### Making Objects Hashable
To use Zig objects as Python dictionary keys:
1. Implement `tp_hash` - hash function (use UUID or unique identifier)
2. Implement `tp_richcompare` - equality comparison (use existing `is_same()` methods for consistency)
3. Register both in type object's `wrap_*` function

### Error Handling
Zig wrappers use "crash on error" philosophy - simplifies error handling by using `defer` for cleanup and letting Python GC handle successfully created objects.

### Building & Testing
- Build: `cd src/faebryk/core/zig && zig build python-ext -Dpython-include=/path/to/python/include`
- Test: `pytest test/core/zig/` (tests use pytest framework)
