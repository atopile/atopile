---
name: Domain Layer
description: "Instructions for electronics-specific logic and build processes: netlists, PCBs, build steps, and exporters."
---

# Domain Layer Module

The `domain layer` (primarily `src/atopile/build_steps.py` and `src/faebryk/exporters/`) encompasses the logic and processes specific to electronic hardware engineering. This includes the build pipeline that transforms a compiled graph into manufacturing artifacts (Gerbers, BOMs, Pick & Place).

## Quick Start

Run the standard build pipeline from a project directory (where `ato.yaml` lives):

```bash
ato build
```

## Relevant Files

- **Build Orchestration**: `src/atopile/build_steps.py`
    - Defines the `Muster` class (a DAG-based task runner).
    - Registers standard build targets: `generate_bom`, `generate_manufacturing_data`, `update_pcb`, etc.
- **Build entry / app init**: `src/atopile/build.py` (constructs app graph from `.ato` or `.py`, runs unit inference)
- **Exporters**: `src/faebryk/exporters/`
    - **pcb/**: KiCad PCB generation and layout sync (`layout_sync.py`).
    - **bom/**: Bill of Materials generation (`jlcpcb.py`, etc.).
    - **netlist/**: Netlist formatting.
    - **documentation/**: Datasheets, diagrams.
- **Layout sync inputs**:
  - `src/atopile/layout.py` (generates `.layouts.json` module→layout mapping)
  - `src/atopile/kicad_plugin/README.md` (plugin workflow overview)

## Dependants (Call Sites)

- **CLI (`src/atopile/cli/build.py`)**: The `ato build` command directly invokes `build_steps.muster` to execute the pipeline.
- **IDE/Extension**: May invoke specific build steps for previews (e.g., `generate_3d_render`).

## How to Work With / Develop / Test

### Core Concepts
- **Muster**: The task runner. Targets declare dependencies (e.g. `generate_bom` depends on `build_design`).
- **Layout Sync**: The process of preserving manual PCB layout changes while updating the netlist/components from the code (`update_pcb`).
- **Artifacts**: Files produced by the build process, stored in the build directory.

### Development Workflow
1.  **Adding a Config Option**: If a new build step needs configuration, add it to `atopile.config` (not covered here, but relevant).
2.  **New Exporters**: Create a new module in `src/faebryk/exporters/` and register a wrapper function in `build_steps.py` using `@muster.register`.

### Testing
- **Integration Tests**: Since this layer orchestrates the whole flow, it is best tested via end-to-end tests or integration tests in `test/end_to_end/` or `test/integration/`.
- **Manual Verification**: Run `ato build` on a sample project and inspect the generated artifacts (Gerbers, BOM csv).
- **Muster unit tests**: `ato dev test --llm test/test_muster.py -q`

## Best Practices
- **Idempotency**: Build steps should generally be idempotent.
- **Virtual Targets**: Use `virtual=True` for targets that just group other targets (e.g. `all` or `default`).
- **Layout Preservation**: Be extremely careful when modifying `update_pcb` or `layout_sync` logic to avoid dataloss of user's manual PCB routing.
