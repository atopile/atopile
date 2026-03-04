---
name: planning
description: "Spec-driven planning for complex design tasks: when to plan, how to write specs as .ato files, and how to verify against requirements."
---

# When to Plan

**Simple tasks — just do it:**
- Single component add/remove/change, value change, rename
- Read/explain code or design
- Fix a specific build error
- Any task with a single clear action

**Complex tasks — ask user, then spec:**
- Multi-component system design (3+ new components interacting)
- New board or subsystem from scratch
- Unclear or function-level requirements ("I need a motor driver", "design me a sensor board")
- Tasks where you need to make multiple architectural choices

**Trigger behavior:** When you detect a complex task, ask the user first:
> "This looks like a multi-part design. Want me to write up a spec first so we're aligned on requirements?"

If the user says yes (or similar), **immediately create the spec file in the same turn** — do not just announce that you will. If they say no or want you to just go, proceed directly with implementation.

# The Spec IS the Design

The spec and the design are **one and the same** `.ato` file. A spec is just the design at a high level of abstraction — skeleton modules, interfaces, constraints, and requirements. As you implement, you fill in real components, pin mappings, and values. The file grows; the structure stays.

**Do not create separate spec files.** The main `.ato` file IS the spec.

**Do not suffix module names with "Spec".** `PowerFrontend`, not `PowerFrontendSpec`. These names persist into the final design — name them for what they are, not for the fact that they started as a spec.

# `has_requirement` — Design Intent

`has_requirement` is the only spec trait. It captures natural language requirements the build can't verify automatically. Place it on whichever module owns the requirement — top-level for system-wide requirements, on a specific subsystem for module-specific ones.

```ato
trait has_requirement<id="R1", text="20A continuous", criteria="FET stage rated for 20A with thermal margin">
```

The spec viewer discovers modules by looking for `has_requirement` traits and groups them by module hierarchy. No other marker trait is needed — if a module has requirements, it shows up in the spec viewer.

These traits stay in the design permanently. They document design intent alongside the implementation.

# Spec Format

```ato
#pragma experiment("TRAITS")
#pragma experiment("BRIDGE_CONNECT")

import ElectricPower
import has_requirement

module BLDCController:
    """
    # BLDC Motor Controller

    One-paragraph overview of what we're building and why.

    ## Key Decisions
    - STM32H723 MCU — motor control timers + Ethernet MAC
    - DRV8300 gate driver — 3-phase, integrated bootstrap

    ## Open Questions
    - Current sensing topology: phase shunt vs low-side?
    """

    # ── Requirements ──────────────────────────────────────
    trait has_requirement<id="R1", text="MCU platform", criteria="Uses STM32H723">
    trait has_requirement<id="R2", text="20A continuous", criteria="FET stage rated for 20A">
    trait has_requirement<id="R3", text="Board size", criteria="40mm x 60mm">

    # ── Architecture ──────────────────────────────────────
    power = new PowerFrontend
    control = new ControlSubsystem
    gate_driver = new GateDriverStage
    comms = new CommsSubsystem

    power.rail_3v3 ~ control.power
    control.pwm ~ gate_driver.control

    # ── Constraints ───────────────────────────────────────
    assert power.vin.voltage within 36V to 60V

module PowerFrontend:
    """Power input and multi-rail regulation."""
    trait has_requirement<id="R4", text="Input protection", criteria="TVS + fuse on input">

    vin = new ElectricPower
    rail_3v3 = new ElectricPower

    assert vin.voltage within 36V to 60V
    assert rail_3v3.voltage within 3.3V +/- 5%

module ControlSubsystem:
    """STM32H723 MCU subsystem."""
    power = new ElectricPower
    pwm = new ElectricLogic

module GateDriverStage:
    """DRV8300 3-phase gate driver + half-bridges."""
    control = new ElectricLogic

module CommsSubsystem:
    """USB-C programming, CAN FD, Ethernet."""
    trait has_requirement<id="R5", text="CAN FD", criteria="Isolated CAN FD transceiver">
```

## How spec concepts map to ato

| Spec Concept | ato Mechanism |
|---|---|
| **Overview** | Module docstring (`"""..."""`) |
| **Architecture** | Sub-modules + connections (`~`) |
| **Requirements** | `trait has_requirement<id, text, criteria>` (on owning module) |
| **Formal constraints** | `assert` statements |
| **Component selection** | `new` instantiations |
| **Sub-system descriptions** | Child module docstrings |
| **Open questions** | Section in docstring |

# Checklist for Tracking Progress

When creating a spec, also create a checklist to track implementation progress. Link checklist items to spec requirements:

```
checklist_create({
  items: [
    {id: "R1", description: "MCU platform", criteria: "Uses STM32H723", requirement_id: "R1"},
    {id: "R2", description: "Gate driver", criteria: "Uses DRV8300", requirement_id: "R2"},
    {id: "step-1", description: "Create project structure", criteria: "ato.yaml + main .ato file exist"}
  ]
})
```

Items with `requirement_id` are linked to the spec's `has_requirement` traits. Items without it are standalone implementation steps.

# Planning Flow

When the user approves planning, execute ALL of steps 1-3 in the SAME turn — do not end your turn after announcing you will plan.

1. **Read** existing project files to understand current state.
2. **Create spec** as the main `.ato` file — `has_requirement` traits on owning modules, sub-module architecture, docstrings, and formal constraints.
3. **Create checklist** linking items to spec requirements.
4. **List Open Questions** — present them to the user for clarification. End your turn here.
5. **Wait for approval.** Do not start implementing until the user confirms the spec.
6. **Execute** requirements one at a time. Mark checklist items as `doing` → `done` as you go. Fill in real components and connections into the existing modules.
7. **Verify.** After all requirements are implemented, run the build and confirm all constraints pass.

# Rules

- Always ask before entering planning mode — never force a spec on a simple task.
- The spec IS the design file — same modules, same names, same structure. It just starts abstract and gets filled in.
- **Do not rename modules** when transitioning from spec to implementation. `PowerFrontend` stays `PowerFrontend`.
- Place `has_requirement` on whichever module owns that requirement, not all on the top-level.
- Update the spec as you learn things (it's a living document).
- If a build fails during implementation, check if the fix still meets requirements before moving on.
- For simple tasks, skip all of this — just implement directly.
- Keep requirements verifiable, not vague.
