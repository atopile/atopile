---
name: ato
description: "Practical ato authoring and review guidance for the current agent workflow: architecture-first design, local package structure, and verified tool recipes."
---

# Design Approach

Start with architecture, not pins. Capture the design as modules, interfaces, docstring requirements, and `assert` constraints before detailed implementation.

Use high-level stdlib interfaces where possible. Check `stdlib_list` and `stdlib_get_item` before creating a new interface.

# Local Package Structure

The current workflow uses nested local package projects.

- `package_create_local` creates `packages/<name>/` with its own `ato.yaml`, `layouts/`, and entry `.ato` file.
- `parts_install(create_package=true)` creates the local package project and installs the raw part into that package project.
- Top-level `ato.yaml` records the package as a file dependency with a local identifier.
- Import local packages using the returned identifier/import statement, typically `local/<slug>/<file>.ato`.
- Discover package targets with `workspace_list_targets`.
- Validate package targets with `build_run(project_path=...)` rather than adding manual top-level build targets by default.

# Wrapper Rules

- Refine the generated package wrapper in place.
- Keep wrappers generic and reusable.
- Expose chip capabilities such as `power`, `i2c`, `spi`, `uart`, `can`, `gpio`, or arrays of stdlib interfaces.
- Keep board-specific grouping and naming in the top-level design.
- Add package-local support parts inside the package project when they are required for the package to build on its own.

# Tool Workflow

## Reuse First

- `packages_search` / `packages_install` for registry packages
- `package_ato_list` / `package_ato_search` / `package_ato_read` for installed package references
- `examples_list` / `examples_search` / `examples_read_ato` for curated examples

## Build a Local Package When Needed

1. Find the part with `parts_search`.
2. Use `web_search` when datasheets or hardware guidance are needed.
3. Install with `parts_install`.
4. Use `create_package=true` when the part should become a reusable local package.
5. Read the generated wrapper and raw part files before editing.
6. Validate the nested package target with `workspace_list_targets`, `build_run(project_path=...)`, and `build_logs_search`.

# Review Heuristics

- Prefer deletion over extra wrapper layers.
- Prefer stdlib interfaces over custom ones.
- Prefer reusable capability boundaries over project-role names.
- Keep verification local first: package target before top-level integration when working on a reusable package.
