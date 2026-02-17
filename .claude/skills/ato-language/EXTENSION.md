# SKILLS

Skills are located in `.claude/skills/`.

# 0.14.x

This release will contain deep core changes.
Primarily using zig and the new graph language.
Also restructuring of what faebryk means.

Primary goals:

- speed
- maintainability
- understanding of the core
- more powerful graph
- serializable graph

### Virtual Environment

- This project uses a uv-managed virtual environment
- If running in interactive shell activate with `source .venv/bin/activate`
- Else run commands with `uv run <command>` prefix

## Graph and Fabll Re-Design

### Graph View and Type Graph Setup

(Implementation: `src/faebryk/core/graph.zig` wrapped in `src/faebryk/core/graph.py`, TypeGraph in `src/faebryk/core/faebrykpy.py`)

To work with the graph, you need a `GraphView` (holds the entire graph state including types and instances) and a `TypeGraph` (manages type definitions).

### Example setting up graph, typegraph, defining type nodes, and instantiating instance nodes

```python
# Setup graph and typegraph
g = fabll.graph.GraphView.create()
tg = fbrk.TypeGraph.create(g=g)

# Parameter Example
parameter_type = F.Parameters.is_parameter.bind_typegraph(tg)
parameter_instance = parameter_type.create_instance(g)

# Electrical Example
# src/faebryk/library/Electrical.py
electrical_type = F.Electrical.bind_typegraph(tg)
electrical_instance = electrical_type.create_instance(g)
```

### Type Definition and Composition

Most entities in the system (Modules, Interfaces, Parameters, etc.) are defined by subclassing `fabll.Node`.

Composition is handled via the `MakeChild()` method, which creates "composition edges". When a class attribute is assigned the result of `SomeType.MakeChild()`, it declares that instances of this new type will contain an instance of `SomeType` as a child. This builds the structural hierarchy of the graph.

Traits, on the other hand, use "trait edges". This is why the syntax differs: traits are attached using `MakeEdge()` (often wrapping `MakeChild()` if creating a new trait instance), whereas structural children use `MakeChild()` directly.

#### MakeChild Example

Using `ElectricPower` (from `src/faebryk/library/ElectricPower.py`) as a baseline:

```python
class ElectricPower(fabll.Node):
    """
    Defines a new type 'ElectricPower' which is a fabll.Node.
    """

    # Composition: ElectricPower contains two Electrical interfaces (hv and lv)
    # MakeChild() creates a definition that these children exist on this type.
    # When ElectricPower is instantiated, hv and lv will also be instantiated as children.
    hv = F.Electrical.MakeChild()
    lv = F.Electrical.MakeChild()

    # Parameters are also children defined via MakeChild, often with arguments
    voltage = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Volt,
    )

    # Traits are attached using MakeEdge combined with MakeChild or specific trait constructors
    # This defines that ElectricPower has the 'is_interface' trait
    _is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
```

### Traits

- Traits are the primary way nodes interact with eachother and functions are executed on nodes
- One or many traits can be applied to type nodes or instance nodes

is_interface trait example making and checking two node connections (assume setup from above)

#### Definition Example

```python
class Electrical(fabll.Node):
	_is_interface = fabll.Traits.MakeEdge(fabll.is_interface.MakeChild())
```

#### Usage Example

```python
e1 = electrical_type.create_instance(g)
e2 = electrical_type.create_instance(g)
e1._is_interface.get().connect_to(e2)
bool connected = e1._is_interface.get().is_connected_to(e2)
```

#### Checking for Traits: Instance Nodes vs Type Nodes

**Instance Nodes** (runtime objects created from types):

```python
instance = some_type.create_instance(g)
instance.has_trait(F.some_trait)
instance.get_trait(F.some_trait)
instance.try_get_trait(F.some_trait)
```

**Type Nodes** (type definitions in the typegraph):

```python
type_bound = SomeType.bind_typegraph(tg)
type_bound.try_get_type_trait(F.some_trait)
type_bound.get_type_trait(F.some_trait)
```

**Key Difference:**

- Instance nodes: `.has_trait()`, `.try_get_trait()`, `.get_trait()`
- Type nodes: `.try_get_type_trait()`, `.get_type_trait()` on `TypeNodeBoundTG`
- `instance.get_type_node()` returns `BoundNodeReference` which has no trait methods - bind the type class instead

### Expressions

Expressions are nodes that represent operations.

`src/faebryk/library/Expressions.py`

```python
anded = F.Expressions.And.bind_typegraph(tg).create_instance(g).setup(
	operand1, operand2
)
```

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

### Error Handling

Zig wrappers use "crash on error" philosophy - simplifies error handling by using `defer` for cleanup and letting Python GC handle successfully created objects.

## Testing

### Overall

Run `ato dev test --llm` in root folder

### Zig Core

`zig build test`

## Test Reports (LLM + Tools)

`ato dev test` writes a single source-of-truth JSON report at `artifacts/test-report.json`.
Derived artifacts:

- `artifacts/test-report.html` (human dashboard)
- `artifacts/test-report.llm.json` (LLM-friendly; ANSI stripped, includes full tests + outputs)

Key fields in `artifacts/test-report.json`:

- `summary` (counts, regressions/fixed/new/removed, truncation stats)
- `run` (argv, pytest args, environment subset, git info, worker stats)
- `tests[]` (nodeid, file/class/function, status/outcome, duration, output preview, output_full logs, memory, worker log path)
- `derived` (failures/regressions/slowest/memory_heaviest/collection_errors)
- `llm` (jq recipes + recommended commands)

LLM usage:

- Prefer JSON over pytest output or HTML; it contains full stdout/stderr/logs/tracebacks (see `output_full`) plus truncation metadata.
- Use jq for precise queries (examples are embedded in the `llm.jq_recipes` field).
- `artifacts/test-report.llm.json` is always generated and has ANSI stripped logs.
- Use `ato dev test --llm` to print a concise summary + schema + jq hints in stdout.
- For LLMs, prefer `ato dev test --llm` over raw `pytest` to get structured context.
- Auto-LLM is enabled for claude-code/codex-cli/cursor; force via `FBRK_TEST_LLM=1` or `FBRK_TEST_LLM=0`.
- Use `ato dev test --reuse --baseline <commit>` to rebuild JSON/HTML/LLM against a new baseline without rerunning tests.
- Use `ato dev test --keep-open` to keep the live report server running after tests finish.
