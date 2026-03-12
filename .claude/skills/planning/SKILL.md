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

**Complex tasks — always plan first:**
- Multi-component system design (2+ ICs interacting)
- New board or subsystem from scratch
- Unclear or function-level requirements ("I need a motor driver", "design me a sensor board")
- Tasks where you need to make multiple architectural choices

**Do not ask whether to plan.** For complex tasks, go straight into planning. Write the spec, create the checklist, call `design_questions` — all in one turn. The user sees the spec and questions, and can steer from there. This is faster than a back-and-forth about whether to plan.

# The Spec IS the Design

The spec and the design are **one and the same** `.ato` file. A spec is just the design at a high level of abstraction — skeleton modules, interfaces, constraints, and requirements. As you implement, you fill in real components, pin mappings, and values. The file grows; the structure stays.

**Do not create separate spec files.** The main `.ato` file IS the spec.

**Do not suffix module names with "Spec".** `PowerSupply`, not `PowerSupplySpec`. These names persist into the final design — name them for what they are, not for the fact that they started as a spec. See the **ato** skill §1.9 for naming guidance.

# Project Structure

Every project with ICs should follow this structure. **IC wrapper packages are separate from the main design.**

```
my-project/
├── ato.yaml                        # Project-level builds defined here
├── main.ato                        # Top-level design — imports packages, not raw parts
├── packages/
│   ├── stm32g474/
│   │   └── stm32g474.ato           # Wrapper: raw pins → standard interfaces
│   ├── drv8317/
│   │   └── drv8317.ato
│   └── tcan3414/
│       └── tcan3414.ato
├── parts/                          # All raw parts (ICs + connectors)
│   ├── STMicroelectronics_STM32G474CBT6/
│   ├── TEXAS_INSTRUMENTS_DRV8317HREER/
│   ├── Changzhou_Amass_Elec_XT30U_M/
│   └── ...
└── layouts/
```

## What goes where

| Item | Location | Why |
|------|----------|-----|
| IC wrapper modules | `packages/<name>/<name>.ato` | Complex pin mapping, reusable |
| All raw parts | `parts/` (project root) | Installed by `parts_install` |
| Simple self-contained parts | Used directly in `main.ato` | No supporting components or high-level interfaces needed (e.g. connectors, LEDs, test points) |
| Generic passives | stdlib (`import Resistor`) | No package needed |
| Top-level design | `main.ato` | Imports wrappers, never raw `_package` |

## Key rules

- **ICs always get wrapper packages** — MCU, gate driver, transceiver, anything with complex pin mapping
- **Wrapper modules expose standard interfaces** — `ElectricPower`, `I2C`, `SPI`, `CAN`, `UART`, `SWD`, `USB2_0`, `USB2_0_IF`, `ElectricLogic`, `ElectricSignal`, not raw pins
- **Check stdlib before defining new interfaces** — if stdlib already has the right interface, or the boundary can be modeled as arrays/composition of stdlib interfaces, use that instead of inventing a project-local interface
- **Wrapper packages are generic** — package boundaries should reflect chip capability, not one board's exact subsystem decomposition or role naming
- **Self-contained parts don't need wrappers** — anything that doesn't need supporting components and doesn't expose high-level interfaces (connectors, LEDs, test points, mounting holes)
- **No `ato.yaml` inside package directories** — package targets are discovered automatically
- **Do not add manual package wrapper build targets to the top-level `ato.yaml`** — use `workspace_list_targets` to discover package targets exposed by local packages

## `ato.yaml` format

```yaml
requires-atopile: ^0.14.0

paths:
  src: ./
  layout: ./layouts

builds:
  default:
    entry: main.ato:DualBLDCController

  # Package builds — for independent testing
  stm32g474:
    entry: packages/stm32g474/stm32g474.ato:STM32G474
    hide_designators: true
  drv8317:
    entry: packages/drv8317/drv8317.ato:DRV8317
    hide_designators: true
```

## Package wrapper pattern

```ato
#pragma experiment("BRIDGE_CONNECT")

import ElectricPower
import CAN
import ElectricLogic
import Capacitor

from "parts/STMicroelectronics_STM32G474CBT6/STMicroelectronics_STM32G474CBT6.ato" import STMicroelectronics_STM32G474CBT6_package

module STM32G474:
    """STM32G474 MCU with decoupling and standard interfaces.

    Exposes:
    - power: 3.3V rail
    - can: CAN FD interface (PA11/PA12)
    - pwm_a: 3x PWM for motor A (TIM1: PA8/PA9/PA10)
    - pwm_b: 3x PWM for motor B (TIM8: PB13/PB14/PB15)
    """

    # ── External interfaces ──
    power = new ElectricPower
    can = new CAN
    pwm_a = new ElectricLogic[3]
    pwm_b = new ElectricLogic[3]

    # ── Package ──
    package = new STMicroelectronics_STM32G474CBT6_package

    # ── Power ──
    power.hv ~ package.VDD
    power.hv ~ package.VDDA
    power.lv ~ package.VSS
    power.lv ~ package.VSSA
    assert power.voltage within 3.3V +/- 10%

    # ── Decoupling ──
    decoupling = new Capacitor[3]
    for cap in decoupling:
        cap.capacitance = 100nF +/- 10%
        cap.package = "C0402"
        power ~> cap ~> power.lv

    # ── CAN ──
    can.tx.line ~ package.PA11
    can.rx.line ~ package.PA12
    can.tx.reference ~ power
    can.rx.reference ~ power

    # ── PWM ──
    pwm_a[0].line ~ package.PA8
    pwm_a[1].line ~ package.PA9
    pwm_a[2].line ~ package.PA10
    pwm_b[0].line ~ package.PB13
    pwm_b[1].line ~ package.PB14
    pwm_b[2].line ~ package.PB15
```

## Clean `main.ato`

```ato
#pragma experiment("BRIDGE_CONNECT")

import ElectricPower

from "packages/stm32g474/stm32g474.ato" import STM32G474
from "packages/drv8317/drv8317.ato" import DRV8317
from "packages/tcan3414/tcan3414.ato" import TCAN3414
from "parts/Changzhou_Amass_Elec_XT30U_M/Changzhou_Amass_Elec_XT30U_M.ato" import Changzhou_Amass_Elec_XT30U_M_package

module DualBLDCController:
    """Dual BLDC motor controller for robot drivetrain."""

    mcu = new STM32G474
    motor_a = new DRV8317
    motor_b = new DRV8317
    can_phy = new TCAN3414

    power = new ElectricPower
    power ~ mcu.power
    power ~ motor_a.motor_supply
    power ~ motor_b.motor_supply

    mcu.can ~ can_phy.can
    mcu.pwm_a ~ motor_a.pwm
    mcu.pwm_b ~ motor_b.pwm
```

The file at `packages/<name>/<name>.ato` is the canonical wrapper boundary for that part or subsystem.
Refine that file in place. `main.ato` should import those wrapper packages directly rather than routing through an extra wrapper aggregator file.

# Requirements in Docstrings

Capture natural-language requirements directly in the module's docstring under a `Requirements:` section. Place requirements on whichever module owns them — top-level for system-wide requirements, on a specific subsystem for module-specific ones.

```ato
module PowerStage:
    """Three-phase MOSFET bridge sized for continuous motor current.

    Requirements:
    - R1: 20A continuous — FET stage rated for 20A with thermal margin
    """
```

Format: `- R<id>: <short text> — <criteria>`

These requirements stay in the design permanently. They document design intent alongside the implementation.

# Spec Format

The spec is the skeleton of the design. It defines architecture, requirements, and constraints — but leaves out implementation details (pin mappings, support circuits). Those get filled in during implementation.

```ato
#pragma experiment("BRIDGE_CONNECT")

import ElectricPower
import CAN
import ElectricLogic

module BLDCController:
    """
    # BLDC Motor Controller

    Dual-motor BLDC controller using STM32G474 and two DRV8317 drivers.

    ## Key Decisions
    - STM32G474 MCU — motor control timers + CAN FD
    - DRV8317 gate driver — 3-phase, integrated LDO

    ## Requirements
    - R1: MCU platform — Uses STM32G474
    - R2: 5-18V input — Operating voltage range
    - R3: Dual motor — 2x DRV8317 in 3-PWM mode

    ## Open Questions
    - Current sensing: phase shunt vs low-side?
    """

    # ── Architecture ──
    power = new PowerSupply
    control = new MCU
    motor_a = new MotorDrive
    motor_b = new MotorDrive
    comms = new CANTransceiver

    power.rail_3v3 ~ control.power
    power.motor_supply ~ motor_a.supply
    power.motor_supply ~ motor_b.supply
    control.pwm_a ~ motor_a.pwm
    control.pwm_b ~ motor_b.pwm
    control.can ~ comms.can

    assert power.vin.voltage within 5V to 18V

module PowerSupply:
    """Power input and regulation."""
    vin = new ElectricPower
    rail_3v3 = new ElectricPower
    motor_supply = new ElectricPower

module MCU:
    """STM32G474 with timers and comms peripherals."""
    power = new ElectricPower
    can = new CAN
    pwm_a = new ElectricLogic[3]
    pwm_b = new ElectricLogic[3]

module MotorDrive:
    """DRV8317 3-phase gate driver."""
    supply = new ElectricPower
    pwm = new ElectricLogic[3]

module CANTransceiver:
    """CAN FD transceiver with UAVCAN connector.

    Requirements:
    - R4: CAN FD transceiver with UAVCAN connector
    """
    can = new CAN
```

## How spec concepts map to ato

| Spec Concept | ato Mechanism |
|---|---|
| **Overview** | Module docstring (`"""..."""`) |
| **Architecture** | Sub-modules + connections (`~`) |
| **Requirements** | `- R<id>: <text> — <criteria>` in module docstring |
| **Formal constraints** | `assert` statements |
| **Component selection** | `new` instantiations |
| **Sub-system descriptions** | Child module docstrings |
| **Open questions** | Section in docstring |

# Checklist for Tracking Progress

When creating a spec, also create a checklist to track implementation progress. Link checklist items to spec requirements:

```
checklist_create({
  items: [
    {id: "spec", description: "Write spec and project structure", criteria: "main.ato with architecture and project-level ato.yaml"},
    {id: "questions", description: "Gather design decisions", criteria: "design_questions called with all open questions"},
    {id: "pkg-mcu", description: "Create MCU wrapper package", criteria: "packages/stm32g474/stm32g474.ato with standard interfaces"},
    {id: "pkg-driver", description: "Create gate driver wrapper package", criteria: "packages/drv8317/drv8317.ato with standard interfaces"},
    {id: "integrate", description: "Wire up top-level design", criteria: "main.ato connects packages through interfaces"},
    {id: "build", description: "Build and verify", criteria: "Build passes or issues clearly identified"},
  ]
})
```

# Planning Flow

The goal is to **front-load all questions and decisions**, then implement without interruption.

## Phase 1: Spec & Ask (end turn after this)

Do steps 1-5 in a SINGLE turn — do not end your turn after announcing you will plan.

1. **Read** existing project files to understand current state.
2. **Set up project structure** — create the project-level `ato.yaml` and `packages/` directories. Do not add manual package-wrapper build targets for generated local packages.
3. **Write the spec** as `main.ato` — architecture with sub-modules, requirements in docstrings, interface connections, and formal constraints. Use standard library interfaces (CAN, I2C, SPI, SWD, USB2_0, ElectricPower, ElectricLogic, ElectricSignal) in the spec instead of inventing local interfaces unless there is a real reusable boundary not covered by stdlib.
4. **Create checklist** with items for each package wrapper + integration + build.
5. **Call `design_questions`** with ALL open questions at once. Include suggested options and recommended defaults where possible — make it easy for the user to answer quickly. Your turn ends automatically after this call.

Use `design_questions` any time you have multiple design decisions to gather. It presents structured questions with bullet-point options that the user can answer or override with freeform text. Do not trickle questions across multiple turns — batch them all into one `design_questions` call.

## Phase 2: Lock decisions (brief)

6. **Wait for user answers.** Incorporate all decisions into the spec and checklist in one pass.

## Phase 3: Implement end-to-end (do not stop)

7. **Create package wrappers** — one per IC. Install parts, inspect vendor datasheets/design guides with `web_search`, map pins to interfaces.
   - Before committing to an unfamiliar IC, motor driver, PMIC, RF part, or other high-risk part, do a brief `web_search` pass to inspect the vendor datasheet/design guide, compare families, confirm the typical topology, and find reference-circuit guidance.
   - Keep wrappers reusable across projects. Expose generic chip capabilities and keep board-specific grouping and role naming in `main.ato` or project modules above the wrapper.
   - Start each wrapper as a basic reusable boundary with the minimum standard interfaces needed to validate the package target and integrate the design. Add more interfaces or alternate pin mappings later only if integration proves they are needed.
   - If a wrapper needs new supporting passives, crystals, or connectors while you are validating that package target, install them into the package project itself with `parts_install(project_path="packages/<name>")`.
   - Once a package project exists and the work is independent, delegate it with `package_agent_spawn(project_path="packages/<name>", goal=..., comments=...)` so the main agent can keep moving on integration and architecture.
8. **Validate package targets first** — use `workspace_list_targets` to discover package targets automatically exposed by local packages, then build/fix wrappers and other submodules before attempting the full design.
   - Build smaller design sections first because they are much faster to validate.
   - Run independent package/submodule builds in parallel where practical to get faster feedback.
   - Do not mark wrapper creation blocked just because the full ideal interface set is not exposed yet. Build the basic wrapper, validate it, and continue expanding it during integration.
   - Use the full-design build only after those smaller targets are green so it serves as an integration check, not the first debugging loop.
9. **Wire up `main.ato`** — connect packages through their interfaces. No raw `_package` imports here.
10. **Build and verify the full design last** — once package and submodule targets are green, run the top-level build and fix integration issues.

**Do not end your turn to ask follow-up questions** — make reasonable assumptions and note them. The user can course-correct via steering messages.

## Phase 4: Report results

10. **Return results** with a concise summary of what changed, build status, and any assumptions you made.

# Rules

- **Do not ask whether to plan** — for complex tasks, just do it. The user sees the spec and can steer.
- The spec IS the design file — same modules, same names, same structure. It just starts abstract and gets filled in.
- **Do not rename modules** when transitioning from spec to implementation. `PowerSupply` stays `PowerSupply`.
- Place requirements in the docstring of whichever module owns them, not all on the top-level.
- **IC wrappers go in `packages/`**, not in `main.ato`. Raw `_package` components are never imported in `main.ato`.
- Update the spec as you learn things (it's a living document).
- If a build fails during implementation, check if the fix still meets requirements before moving on.
- For simple tasks, skip all of this — just implement directly.
- Keep requirements verifiable, not vague.
