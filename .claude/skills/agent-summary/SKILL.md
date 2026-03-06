---
name: agent-summary
description: "Generate short live progress summaries for the atopile agent from recent tool events, preambles, checklist changes, and build state. Use for ephemeral UI activity text only, never for transcript replies or autonomous reasoning."
---

# Purpose

This skill is for a lightweight summary model that makes the agent feel alive while it works.

It does not plan, reason, or steer the task.
It only rewrites recent real events into one short live status line for the UI.

# Inputs

The summarizer should receive a small structured window, for example:

- current phase
- latest model preamble
- last 3-8 meaningful tool events
- latest checklist delta
- latest build/run status
- touched files or targets when available

Only summarize what is present in the input.

# Output Contract

Return exactly one short progress line.

Rules:

- 6-16 words preferred
- one sentence fragment, no bullet, no prefix
- present tense
- no first person
- no user instructions
- no questions
- no claims about completion unless the input says so
- no speculation about hidden work
- no mention of internal implementation details unless directly useful

Good:

- `Reviewing the motor driver package layout and pin mapping`
- `Editing the STM32 wrapper and tightening power constraints`
- `Running a build to validate the new package targets`
- `Checking build errors against the updated driver modules`

Bad:

- `I am thinking about how to solve this`
- `The agent is almost done`
- `Working hard on your request`
- `Maybe updating the power stage and probably the MCU too`
- `Would you like me to run a build?`

# Priority

Prefer the most concrete current activity:

1. error or stopped state
2. waiting on user input
3. active build or build review
4. active file edits
5. part/package search or vendor-document research
6. planning or general review

If multiple events exist, summarize the most recent meaningful step, not the whole history.

# Event Interpretation

Use these patterns:

- `project_read_file`, `project_search`, `project_list_*`: reviewing or inspecting
- `project_edit_file`, `project_create_*`, `project_move_path`: editing or restructuring
- `parts_search`, `parts_install`: selecting or installing parts
- `packages_search`, `packages_install`, `package_create_local`: creating or wiring packages
- `web_search`: checking vendor datasheets, design guides, or application notes
- `build_run`: running a build
- `build_logs_search`, `design_diagnostics`: reviewing failures or diagnostics
- checklist `doing -> done`: moving from one milestone to the next

Prefer file names, package names, target names, or subsystem names when available.

# Safety

Never invent:

- files that were not touched
- parts that were not searched or installed
- build results that were not reported
- design choices that were not made
- progress beyond what the event stream supports

If the input is vague, stay vague but still concrete:

- `Reviewing the current project structure`
- `Planning the next implementation step`

# Usage

This summary is ephemeral UI state only.

Do not:

- write to the transcript
- create assistant chat messages
- replace tool traces
- replace checklist updates

It is a presentation layer over real events, not a source of truth.
