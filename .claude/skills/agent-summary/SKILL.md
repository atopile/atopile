---
name: agent-summary
description: "Generate one short live status line for the atopile agent UI from recent real events. Use only for ephemeral progress text, never for transcript replies or planning."
---

# Purpose

This skill rewrites recent real activity into one short progress line for the UI.

It does not plan, reason, or invent work.

# Input

Summaries should only use what is present in the provided event window, typically:

- current phase
- latest model preamble
- recent tool events
- latest checklist change
- latest build state

# Output Contract

Return exactly one short line.

Rules:

- 6-16 words preferred
- sentence fragment, not a bullet
- present tense
- no first person
- no questions
- no speculation
- no completion claims unless the input says work is done

# Priority

Prefer the most concrete current activity in this order:

1. error or stopped state
2. waiting on design questions
3. active build or build-log review
4. active file edits
5. package or part research/installation
6. general review

# Event Mapping

Use these patterns:

- `project_read_file`, `project_search`, `project_list_*`: reviewing
- `project_edit_file`, `project_create_*`, `project_move_path`, `project_rename_path`, `project_delete_path`: editing
- `parts_search`, `packages_search`, `web_search`: researching
- `parts_install`, `packages_install`, `package_create_local`: installing or creating a package
- `workspace_list_targets`: discovering build targets
- `build_run`: running a build
- `build_logs_search`: reviewing build failures or status
- checklist item progress: moving to the next task

Prefer concrete file names, package names, targets, or subsystem names when available.

# Safety

Never invent:

- files that were not touched
- parts or packages that were not searched or installed
- build results that were not reported
- progress beyond what the event stream supports
