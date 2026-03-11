---
name: planning
description: "Planning guidance for complex ato design tasks: when to write a spec first, how to structure local packages, and how to hand off implementation cleanly."
---

# When To Plan

Plan first for:

- new boards or subsystems
- multi-component work with several interacting ICs
- requests with unresolved architectural choices

Do not stop to ask whether planning is needed. If the task is clearly complex, write the spec and gather open decisions in one pass.

# Planning Deliverable

The plan should leave the project ready for implementation:

- a high-level `main.ato` design or updated top-level design
- requirements captured in docstrings on the modules that own them
- interface-level wiring and `assert` constraints
- a checklist for the implementation work
- one `design_questions` call if real open questions remain

# Current Package Structure

Local packages are nested projects, not just extra source files.

- `package_create_local` creates `packages/<name>/` with its own `ato.yaml`, `layouts/`, and entry module.
- `parts_install(create_package=true)` creates the same package-project structure and installs the raw part inside it.
- The parent project records the package as a file dependency.
- Imports should use the returned local identifier/import statement, typically `local/<slug>/<file>.ato`.
- Package validation should use `workspace_list_targets` and `build_run(project_path=...)`.

# Planning Rules

- Keep the top-level design architecture-first.
- Use stdlib interfaces where possible.
- Keep reusable wrapper boundaries inside local packages.
- Keep project-specific naming and composition at the top level.
- Add manual build targets only when the project genuinely needs them, not just to validate a nested local package.

# Suggested Flow

1. Read the current project structure and constraints.
2. Update or create the top-level design skeleton.
3. Decide which reusable packages are needed.
4. Create the checklist.
5. Call `design_questions` once if unresolved decisions remain.
