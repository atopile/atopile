---
name: package-agent
description: "Guidance for working on one local package project: package scope, wrapper boundaries, package-local dependencies, and nested-package validation."
---

# Scope

Own one local package project under `packages/<name>/`.

Stay inside that package project unless the parent design must change to integrate the finished package.

# What A Local Package Is

In the current repo, a local package is a nested project with:

- its own `ato.yaml`
- its own `layouts/`
- an entry `.ato` file
- a file-dependency identifier added to the parent project

Import the package using that identifier, typically `local/<slug>/<file>.ato`.

# Wrapper Rules

- Keep the wrapper generic and reusable.
- Expose capabilities, not board-role names.
- Prefer stdlib interfaces and simple arrays/composition over custom aggregate interfaces.
- Refine the generated wrapper in place instead of adding another wrapper layer.

# Supporting Parts

If the package needs passives, crystals, regulators, or connectors to build correctly in isolation, install them into that package project with `parts_install(project_path=...)`.

# Validation Workflow

1. Read the wrapper and any imported raw part files.
2. Make one coherent package change at a time.
3. Use `workspace_list_targets` to discover the package targets.
4. Run `build_run` with `project_path` pointing at the package project.
5. Use `build_logs_search` to fix the next concrete failure.

# Finish Bar

Stop when the package is minimally complete, reusable, and validates through its own package target.
