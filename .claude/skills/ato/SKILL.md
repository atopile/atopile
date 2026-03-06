---
name: ato
description: "Authoritative ato authoring and review skill: language reference, stdlib, design patterns, and end-to-end board design workflow."
---

# 1. End-to-End Design Process

This is the canonical sequence for designing a board in atopile. Move quickly, keep the structure clean, and avoid spreading planning state across multiple rounds unless the design genuinely requires it.

## Step 1: Draft The Architecture

Capture user intent as ato code immediately. Start with a clean high-level architecture and only stop to ask batched design questions when there are real unresolved decisions.

Focus on:

- What the system is supposed to do
- The main functional blocks
- The important interfaces and voltage domains
- Key constraints on size, cost, power, or manufacturing
- Any parts or protocols that are already fixed by the user

> **Tools:** Use `design_questions` to batch multiple unresolved decisions at once. Use `web_search` if you need to research unfamiliar domains or components before locking the architecture.

Gate: a spec `.ato` file exists with module hierarchy, interface connections, requirements in docstrings, and formal constraints.

## Step 2: Write The Spec

The spec IS the design file at a high level of abstraction. As you implement, you fill in real components and wiring. The file grows; the structure stays.

**Key principles:**
- **Good naming** — name modules by their role in the system, not implementation topology (see Section 1.1).
- **Module boundaries** should encapsulate common functionality to avoid duplication at the top level.
- **Use high-level interfaces** (`ElectricPower`, `I2C`, `SPI`, `UART`, `ElectricLogic`) instead of low-level electrical connections where possible.
- **Custom interfaces are rare** — before defining a new `interface`, check the stdlib first with `stdlib_list` / `stdlib_get_item`. If an existing stdlib interface or a simple composition/array of stdlib interfaces works, use that instead.
- **Capture requirements** in the module docstring under a `Requirements:` section on the module that owns them.
- **Add formal constraints** with `assert` for voltage, current, frequency bounds.
- **Wire modules together** at the interface level (`~`). Do NOT wire pins yet.

**Step-by-step:**

1. **Break the request into subsystems.** Each functional block becomes a `module` — power, MCU, sensors, comms, IO, etc.
2. **Define interfaces at module boundaries.** Use stdlib interfaces to declare how modules connect.
3. **Capture requirements in docstrings.** Add a `Requirements:` section to the docstring of the module that owns each requirement.
4. **Add formal constraints** with `assert` for voltage, current, frequency bounds.
5. **Wire modules together** at the interface level (`~`).
6. **Create a checklist** linking items to requirement IDs for tracking.

**Example spec:**

```ato
import ElectricPower
import I2C
import SPI
import ElectricLogic

module SensorBoard:
    """
    # Environmental Sensor Board

    Battery-powered sensor node with temperature, humidity, and
    pressure sensing, BLE comms, and USB-C charging.

    ## Requirements
    - R1: BLE connectivity — nRF52840 with BLE 5.0
    - R2: Environmental sensing — BME280 for temp/humidity/pressure
    - R3: USB-C charging — 5V USB-C input with charge IC
    - R4: Board size — 25mm x 30mm max

    ## Key Decisions
    - nRF52840 for BLE + low power
    - BME280 for temp/humidity/pressure

    """

    # ── Architecture ──────────────────────────────────────
    power = new PowerSupply
    mcu = new MCU
    sensors = new EnvironmentalSensor
    comms = new Radio

    # Interface-level wiring (no pins yet)
    power.rail_3v3 ~ mcu.power
    power.rail_3v3 ~ sensors.power
    mcu.i2c ~ sensors.i2c
    mcu.spi ~ comms.spi

    # ── Constraints ───────────────────────────────────────
    assert power.usb_in.voltage within 4.5V to 5.5V
    assert power.rail_3v3.voltage within 3.3V +/- 5%

module PowerSupply:
    """
    USB-C input, charge controller, LDO regulation.

    ## Requirements
    - R5: Battery charging — LiPo charge IC with thermal protection
    """

    usb_in = new ElectricPower
    battery = new ElectricPower
    rail_3v3 = new ElectricPower

module MCU:
    """nRF52840 with crystal, decoupling, and debug header."""
    power = new ElectricPower
    i2c = new I2C
    spi = new SPI

module EnvironmentalSensor:
    """BME280 environmental sensor."""
    power = new ElectricPower
    i2c = new I2C

module Radio:
    """BLE antenna matching and RF front end."""
    spi = new SPI
```

**Key rules for this step:**
- Module names are final — `PowerSupply` stays `PowerSupply` through implementation. Do NOT suffix with "Spec".
- Place requirements in the docstring of the module that owns them, not all on the top-level.
- Use docstrings for overview, requirements, and important decisions.
- Do not keep unresolved planning state in the design file longer than needed; use `design_questions` to batch open questions and then continue implementation.

> **Tools:** Use `stdlib_list` / `stdlib_get_item` to check available interfaces and components before defining custom ones. Use `examples_search` / `examples_read_ato` to find reference designs for similar systems.

Gate: architecture is coherent enough to implement. If there are multiple open design decisions, batch them with `design_questions` and continue once answers arrive.

## Step 3: Resolve Open Decisions

Present the user with the current architecture and any real unresolved decisions:

- List the modules and their responsibilities.
- Show the interface connections between modules.
- Highlight any key decisions or trade-offs made.
- Call out any assumptions or areas where alternatives exist.

Use `design_questions` to batch unresolved decisions instead of trickling follow-up questions across multiple turns. Then incorporate the answers directly into the spec and continue implementation.

Gate: the key open questions are resolved or reasonable defaults have been chosen.

## Step 4: Implement Detailed Design

Now fill in the spec with real components, wiring, and constraints. This step covers package search, part selection, and detailed wiring.

### 4a: Find existing packages

Search the atopile package registry before building from scratch.

> **Tools:** `packages_search` → `packages_install` → `package_ato_read` to inspect public interface. Also check `stdlib_list` for built-in modules.

- Prefer reusing a well-tested package over writing a new driver module.

### 4b: Create local packages when none exist

When `packages_search` returns no match for a needed IC, connector, or module, **create a local driver package** instead of giving up or asking the user to find one.

> **Tools:** `parts_search` → `web_search` (to compare families, inspect the vendor datasheet/design guide, validate topology, and find reference circuits) → `parts_install(create_package=true)` → `project_read_file` (to inspect the generated wrapper package) → `project_edit_file` (to refine that wrapper in place) → `workspace_list_targets` (to discover nested package targets).

**Step-by-step recipe:**

1. **Find the part**: Use `parts_search` to find the LCSC component (e.g., `parts_search("LAN8742A")`).
2. **Research the part family when needed**: Use `web_search` before locking the part if you need application notes, common reference circuits, family comparisons, or confirmation that the chosen topology is standard and robust.
3. **Install as a local package**: Use `parts_install` with the LCSC ID and `create_package=true`. This installs the raw part and generates the canonical reusable wrapper package under `packages/`.
4. **Inspect the vendor docs with web search**: Use `web_search` with the part number, vendor, and terms like `datasheet`, `hardware design`, `application circuit`, `decoupling`, `pinout`, or the specific pins/features you need.
5. **Read the generated files**: Inspect the generated wrapper under `packages/<PartName>/<PartName>.ato` and the installed raw part it imports to see available interfaces and exact pin names.
6. **Refine the wrapper package** if needed:
   - Treat `packages/<PartName>/<PartName>.ato` as the canonical wrapper module for that part.
   - Edit that generated package file in place rather than creating another wrapper layer.
   - Keep the raw installed part file unchanged.
   - Start with a basic reusable wrapper first. Expose the minimum standard interfaces needed to build the package and integrate it cleanly.
   - Keep the wrapper generic and reusable. Expose the chip's general capabilities, not one project's exact architecture.
   - Expose standard interfaces such as `ElectricPower`, `I2C`, `SPI`, `UART`, `CAN`, `SWD`, `USB2_0`, `USB2_0_IF`, `ElectricLogic`, or `ElectricSignal`.
   - Before writing any custom `interface`, check `stdlib_list` / `stdlib_get_item` for an existing stdlib interface and prefer stdlib arrays/composition over project-local aggregate interfaces.
   - Prefer capability-oriented names and boundaries such as `uart`, `spi`, `adc_inputs`, `gpio`, `usb`, `swd`, `power`, not design-specific roles like `sbus`, `phase_current`, `weapon_pwm`, or `battlebot_interfaces`.
   - It is fine to make slightly opinionated pin choices so key capabilities are wired out cleanly, but do not encode one specific end design into the wrapper shape.
   - Do not treat incomplete pin exposure as a blocker. Add more interfaces, alternate pin mappings, or richer capabilities later when integration proves they are needed.
   - Map the internal `_package` component pins to those interfaces.
   - Add decoupling capacitors and required passives.
   - Set voltage/current constraints from the datasheet.
7. **Discover targets**: Run `workspace_list_targets` after package creation to inspect and build the package targets that were exposed automatically.
8. **Import and use** the local package in your top-level design directly from `packages/<PartName>/<PartName>.ato`.

**Example: refining a generated local I2C mux wrapper**

The generated package file under `packages/<PartName>/<PartName>.ato` is the wrapper you should refine. The raw part component it imports is not the place to edit behavior.

```ato
#pragma experiment("BRIDGE_CONNECT")

import ElectricPower
import ElectricLogic
import I2C
import Capacitor
import Resistor

from "parts/Texas_Instruments_TCA9548APWR/Texas_Instruments_TCA9548APWR.ato" import Texas_Instruments_TCA9548APWR_package

module TI_TCA9548A:
    # Public interfaces
    power = new ElectricPower
    assert power.voltage within 1.65V to 5.5V

    i2c = new I2C
    reset = new ElectricLogic

    # Instantiate the auto-generated package component
    package = new Texas_Instruments_TCA9548APWR_package

    # Power connections
    power.hv ~ package.VCC
    power.lv ~ package.GND

    # I2C — connect via .line and .reference
    i2c.sda.line ~ package.SDA
    i2c.scl.line ~ package.SCL
    i2c.sda.reference ~ power
    i2c.scl.reference ~ power

    # Decoupling — use bridge connect (~>) for series path
    decoup_100n = new Capacitor
    decoup_100n.capacitance = 100nF +/- 20%
    decoup_100n.package = "0402"
    power.hv ~> decoup_100n ~> power.lv

    decoup_2u2 = new Capacitor
    decoup_2u2.capacitance = 2.2uF +/- 20%
    decoup_2u2.package = "0402"
    power.hv ~> decoup_2u2 ~> power.lv

    # Reset with pullup
    reset.line ~ package.nRESET
    reset.reference ~ power
    reset_pullup = new Resistor
    reset_pullup.resistance = 10kohm +/- 1%
    reset_pullup.package = "0402"
    reset.line ~> reset_pullup ~> reset.reference.hv
```

**Key rules:**
- Always `parts_install` first — never reference a part that hasn't been installed.
- Prefer `parts_install(create_package=true)` for ICs and other reusable wrapped parts.
- Use `package_create_local` only when you need an empty local package scaffold without installing a physical part.
- Always **read the generated package and raw part `.ato` files** to see the exact signal names (e.g., `package.VCC`, `package.SDA`). Do NOT guess pin names.
- Always use `web_search` to inspect the vendor datasheet and hardware design notes to get correct pin mapping, constraints, and recommended decoupling.
- The generated package file under `packages/` is the canonical wrapper for that part. Refine it in place.
- The raw installed file is a `component` — never edit it.
- Build a basic reusable wrapper first. Expose the minimum standard interfaces needed to validate the package and integrate it, then come back and add more pin mappings or interfaces later if integration requires them.
- Instantiate the raw component inside the wrapper as `package = new <ComponentName>`.
- `main.ato` should import wrapper packages directly from `packages/<name>/<name>.ato`, not through an extra aggregator wrapper file.
- Connect interfaces via `.line` and `.reference` (e.g., `i2c.sda.line ~ package.SDA`; `i2c.sda.reference ~ power`).
- Use bridge connect `~>` for decoupling caps in series (e.g., `power.hv ~> cap ~> power.lv`).
- Use `.capacitance` for Capacitor values, `.resistance` for Resistor values (NOT `.value`).
- Add `#pragma experiment("BRIDGE_CONNECT")` if using `~>`.
- Keep IC-specific pin wiring inside the driver module; expose only abstract interfaces.
- Do NOT skip this step and tell the user to create the package themselves. This is core agent capability.

### 4c: Part selection

Choose components using generics + constraints wherever possible.

> **Tools:** `parts_search` / `parts_install` for specific ICs/connectors. `web_search` for vendor datasheets, hardware design guides, application notes, and alternative parts.

- Use stdlib generics (`Resistor`, `Capacitor`, `Inductor`, `Diode`, `LED`, `Fuse`) with value + package constraints for auto-picking. Prefer generics over locked parts.
- Use `parts_search` only when a specific part is needed (IC, connector, specialized component).
- Use `web_search` before locking a part when you need to compare candidate families, confirm the recommended implementation pattern, or find a solid reference circuit/application note.
- Use `parts_install` for parts that need explicit LCSC IDs, and prefer `create_package=true` when the part should become a reusable local wrapper.
- Use `web_search` after selecting a concrete part to inspect the vendor datasheet, exact pins, limits, and supporting circuitry.
- Lock only high-risk parts (MCU, PMIC, RF, connectors). Leave commodity passives auto-picked.
- Before inventing a project-local `interface`, check whether the wrapper boundary can be represented as:
  - a stdlib interface (`SPI`, `UART`, `SWD`, `USB2_0_IF`, etc.)
  - an array of stdlib signals/interfaces (`new ElectricLogic[3]`, `new ElectricPower[3]`, `new ElectricSignal[3]`)
  - a few named stdlib fields directly on the module
- Only define a custom interface when it represents a real reusable protocol/boundary that stdlib or simple composition does not already cover.
- Keep package wrappers generic. Design-specific grouping and role naming belong in `main.ato` or project modules above the package layer.

### 4d: Detailed wiring and constraints

Wire connectivity, add constraints and equations, complete the design.

- Wire modules through interfaces using `~` (or `~>` for bridge/series paths).
- Add parameter constraints (`assert ... within ...`) for all key electrical properties.
- Add decoupling, pullups, and protection per Section 4 patterns.

Gate: design is complete — all modules wired, all constraints declared, all interfaces connected. Every component is either a constrained generic or an explicitly selected part.

## Step 5: Build

Run builds and fix issues iteratively until everything passes. **Build submodules first** (if applicable) — it is much easier to get small chunks working before running the full build.

### 5a: Build + fix loop

> **Tools:** `workspace_list_targets` → `build_run` → `build_logs_search` (filter by `log_levels`/`stage`) → `design_diagnostics` for silent failures. Use `report_variables` to inspect constraint state and `report_bom` to verify part selection.

- Run `workspace_list_targets` first after creating/installing local packages so you know which package targets already exist automatically.
- Split the design into sensible submodules and build those smaller targets first. This is the default validation loop.
- Build wrapper/package targets first, and do so in parallel where practical, so you get feedback much faster than waiting on repeated full-design builds.
- If a wrapper is only partially exposed, still build the basic wrapper and keep moving. Extend the wrapper later during integration instead of marking the work blocked just because more interfaces may be needed.
- Fix submodule/package failures before running the top-level design.
- Do not add manual top-level `ato.yaml` entries just to build generated local package wrappers if `workspace_list_targets` already exposes those targets.
- Use the full top-level build after submodules are green; it should then be mainly an integration check rather than the first place issues appear.
- Check `build_logs_search` for errors/warnings.
- Use `design_diagnostics` for silent failures.
- Fix issues using Section 5 troubleshooting.
- Repeat until build passes cleanly.

## Step 6: Summary

> **Tools:** Use `report_bom` for parts list and `report_variables` for constraint summary when preparing the summary.

When the build finishes, give the user a summary:

- **What was built** — list the modules, key components, and interfaces.
- **Blockers or issues** — note any problems encountered and how they were resolved (or if they remain).
- **Suggestions for next steps** — what the user might want to do next (e.g., review placement, order boards, add features, run DRC).

Gate: user has received a clear summary and knows the state of the design.

---

## 1.1 Module Naming

Name modules the way you'd label blocks on a system block diagram — by their **role in the system**, not their implementation topology. Avoid generic suffixes like `Subsystem`, `Unit`, `Block`, or `Section`.

**Good names:**

- `PowerSupply` — input protection, regulation, and distribution
- `PowerInput` — connector, reverse polarity protection, and bulk decoupling
- `BatteryCharger` — charge IC, sense resistors, and status output
- `BMS` — cell balancing, protection, and fuel gauge
- `GateDriver` — bootstrap, dead-time, and level shifting for a FET bridge
- `MotorDrive` — integrated driver with current limit and fault output
- `CurrentSense` — shunt and sense amplifier
- `CANTransceiver` — transceiver, termination, and ESD (don't use `CAN` — it shadows the stdlib interface)
- `USBPort` — connector, ESD, and pull-ups (don't use `USB` — too generic, may shadow stdlib types)
- `EthernetPHY` — PHY, magnetics, and RJ45
- `Radio` — RF front end, antenna match, and balun
- `IMU` — accelerometer/gyro with decoupling
- `ADCInput` — anti-alias filter, reference, and input scaling
- `LevelShift` — voltage translation between power domains
- `InputFilter` — common-mode choke and filter caps
- `Clock` — crystal or oscillator with load caps
- `Debug` — SWD/JTAG connector and pull-ups
- `Indicators` — status LEDs with current-limiting resistors
- `Protection` — ESD, TVS, or overvoltage clamping on an interface

IC wrapper packages use the **part name** directly: `STM32G474`, `DRV8317`, `TCAN3414`.

Inside a module, names get more specific — a `PowerSupply` module might contain a `BuckConverter` and an `LDO`. The name should match the level of abstraction: system-level blocks use system-level names.

When in doubt, ask: *"what would this block be labelled on a system block diagram?"*

## 1.2 Architecture Decomposition

For non-trivial designs, split early and keep one primary module per file.

**Complexity triggers that force splitting:**
- More than 40 connect statements in one module
- More than 12 direct package-pin connections in one module
- More than 10 child instances in one module
- Mixed concerns (power conversion + MCU + comms + connectors in one module)
- Duplicated wiring clusters that could be a reusable child module

**Example file layout:**

```text
main.ato                    # integration module only
ato.yaml                    # project-level builds
packages/
  stm32g474/
    stm32g474.ato           # reusable wrapper package
power/
  buck_5v.ato               # project-specific power stage
  buck_3v3.ato              # project-specific regulator stage
control/
  motor_control.ato         # project-specific control module
io/
  connectors.ato            # project-specific adapters/connectors
```

Keep `main.ato` at the project root. Put reusable IC wrappers under `packages/`. Put project-specific implementation modules in sibling folders only when they help keep the design clean.

## 1.3 Design for Test

Imagine the board comes back from the factory, gets plugged in, and it's your job to bring it up — automatically, at scale. Design with that scenario in mind from the start.

### Think about the bringup flow

Before wiring, walk through the commissioning sequence in your head:

1. **Power on** — how does it get power? USB? Bench supply? Battery? What's the first thing that should happen?
2. **Programming** — how does firmware get loaded? SWD/JTAG header? USB bootloader? Is the debug connector accessible?
3. **Configuration** — does the device need provisioning (keys, calibration, IDs)? What interface is used?
4. **Verification** — how do you confirm each subsystem works? What can you measure?
5. **Final state** — what does "pass" look like? An LED? A USB enumeration? A message on a bus?

Include the connectors, headers, and test points needed for this flow in your design. A debug header that gets cut to save $0.10 will cost hours during bringup.

### Self-measurement of critical rails

Every power rail that matters should be observable — ideally by the MCU itself, not just a multimeter:

- **ADC sense dividers** on critical voltage rails (battery, main supply, regulated outputs) so firmware can read and report rail health.
- **Current sense** on high-power paths (motor drives, charging) for monitoring and fault detection.
- **Test points** on rails that can't be ADC-measured, so they're accessible with a probe during bringup.

```ato
# Example: ADC-measurable voltage rail
adc_sense = new ResistorVoltageDivider
power_12v.hv ~> adc_sense ~> power_12v.lv
adc_sense.output ~ mcu.adc[0]
assert adc_sense.ratio within 0.2 to 0.3   # scale 12V into MCU ADC range
```

### Practical checklist

When designing, ask yourself:

- **Programming**: Is there a debug header (SWD/JTAG) or USB bootloader path? Is it accessible after assembly?
- **Power rails**: Can the MCU read the key voltage rails via ADC? Are there test points on rails it can't read?
- **Communication buses**: Is there a way to verify each bus is alive? (e.g., I2C scan, SPI loopback, UART console)
- **Indicators**: Are there status LEDs that show power-good, heartbeat, or error states?
- **Isolation**: Can subsystems be tested independently? (e.g., can you power the MCU without the motor driver?)
- **Test points**: Are critical signals (clocks, resets, key nets) accessible for probing?
- **Connectors**: Are debug/programming connectors placed where they won't be blocked by enclosures or other boards?

---

# 2. Language Reference

ato is a **declarative** language for defining electronics. Every statement constructs graph nodes and edges or declares constraints — there is no runtime execution order. This section covers the language by concept with practical examples.

## 2.1 Blocks

Three block kinds exist: `module`, `component`, and `interface`.

```ato
module PowerSupply:
    """Regulate 5V input down to 3.3V."""
    pass

component MyChip:
    pin VCC
    pin GND

interface MyBus:
    signal data
    signal clock
```

- Use `module` for reusable hardware building blocks with components and equations.
- Use `interface` for reusable connectable bus/signal/power abstractions.
- Use `component` for physical parts with pin mappings (usually auto-generated — you rarely write these by hand).

**Inheritance** specializes a block:

```ato
module USB2_0TypeCVerticalConnector from USBTypeCConnector_driver:
    connector -> VerticalUSBTypeCConnector_model
```

**Rules:**
- Nested block definitions are NOT allowed — all blocks must be at file top-level.
- Duplicate symbol names in the same scope are errors.
- Use docstrings (triple-quoted strings) as the first statement for module documentation.

## 2.2 Instances

Create instances with `new`. Bare type assignment is invalid.

```ato
# Good
r = new Resistor
caps = new Capacitor[4]

# Bad — will error
r = Resistor
```

**Arrays** create indexed sequences:

```ato
leds = new LED[8]
leds[0].lcsc_id = "C2286"
leds[3].lcsc_id = "C2297"
```

**Templated construction** (requires `MODULE_TEMPLATING` pragma):

```ato
#pragma experiment("MODULE_TEMPLATING")

addressor = new Addressor<address_bits=3>
```

## 2.3 Fields and Access

Access fields with dotted paths and array indexing:

```ato
power                          # local field
power.hv                       # sub-field
i2c.sda.line                   # nested access
gpio[0].line                   # indexed access
microcontroller.uart[0].tx     # deep path
```

**Declare typed parameters** with unit annotation:

```ato
v_in: V
v_out: V
max_current: A
ratio: dimensionless
```

Declared parameters can then be used in equations and constraints.

## 2.4 Connections

### Direct connect: `~`

Use for net-level or interface-level equivalence. This is the primary connection operator.

```ato
power_3v3 ~ sensor.power       # interface-level
i2c_bus ~ sensor.i2c            # bus-level
gpio.line ~ package.PA0         # signal-level
```

When you connect interfaces, all matching sub-fields connect recursively.

### Bridge connect: `~>` (requires `BRIDGE_CONNECT` pragma)

Use for series/inline topology through bridgeable elements:

```ato
#pragma experiment("BRIDGE_CONNECT")

power_in ~> fuse ~> ldo ~> power_out      # power path
power.hv ~> cap ~> power.lv               # decoupling
data_in ~> led_strip ~> data_out           # daisy chain
```

Bridge connect traverses `can_bridge` trait paths (in/out). Only use when the module is physically in series.

**Rules:**
- Do NOT mix directions in one statement: `a ~> b <~ c` is invalid.
- Both `~>` and `<~` exist but keep chains in one direction.

## 2.5 Constraints

Use `assert` to declare constraints over parameter domains.

### `within` — for bounds and ranges (preferred for values)

```ato
assert power.voltage within 3.3V +/- 5%
assert power.voltage within 1.8V to 5.5V
assert i2c.frequency within 100kHz to 400kHz
```

### `is` — for expression identity between parameters

```ato
assert addressor.address is i2c.address
assert v_out is v_in * r_bottom.resistance / r_total
assert r_total is r_top.resistance + r_bottom.resistance
```

### Comparison operators

```ato
assert power.voltage >= 3.0V
assert max_current <= 500mA
assert inductor.max_current >= peak_current
```

**Rules:**
- Use `within` for literal/range bounds. Use `is` for relating expressions/parameters.
- Avoid `assert x is 3.3V` (deprecated) — use `assert x within 3.3V +/- 0%` instead.
- Only one comparison per assert — `assert 1V < x < 5V` is NOT supported. Split into two asserts.
- Supported operators: `>`, `>=`, `<`, `<=`, `within`, `is`.

## 2.6 Quantities and Units

### Singleton

```ato
3.3V
10kohm
100nF
2.4MHz
1A
```

### Bounded range

```ato
1.8V to 5.5V
100kHz to 400kHz
0.5mA to 3mA
```

### Bilateral tolerance (absolute)

```ato
10kohm +/- 1kohm
3.3V +/- 0.2V
```

### Bilateral tolerance (relative)

```ato
10kohm +/- 5%
3.3V +/- 5%
```

### Unitless values

```ato
ratio: dimensionless
ratio = 0.5
assert ratio within 0.1 to 0.9
```

### Arithmetic

Supported operators: `+`, `-`, `*`, `/`, `**`, parentheses `()`.

```ato
assert resistor.resistance is (power.voltage - led.forward_voltage) / current
assert peak_current is (i_out / (efficiency * (1 - duty))) + ((v_in * duty) / (2 * f_sw * l))
```

**Rules:**
- Both sides of a range/tolerance must have commensurable units (`3.3V to 5A` is invalid).
- `|` and `&` operators parse but are rejected semantically — never use them.
- Common unit symbols: `V`, `A`, `ohm`/`kohm`/`Mohm`, `F`/`uF`/`nF`/`pF`, `Hz`/`kHz`/`MHz`, `W`, `H`/`uH`, `mm`. SI prefixes (`m`, `u`, `n`, `k`, `M`) are supported.

## 2.7 Imports

### Bare import — stdlib only

```ato
import ElectricPower
import I2C
import Resistor
import Capacitor
```

Bare `import X` must resolve to a stdlib-allowlisted type or trait. If not allowlisted, you get a `DslImportError`.

### Path import — packages and local files

```ato
from "atopile/ti-tlv75901/ti-tlv75901.ato" import TI_TLV75901
from "packages/stm32g474/stm32g474.ato" import STM32G474
from "parts/Texas_Instruments_TCA9548APWR/Texas_Instruments_TCA9548APWR.ato" import Texas_Instruments_TCA9548APWR_package
from "./power/buck_5v.ato" import Buck5V
```

**Rules:**
- One import per line (multi-import `import A, B` is deprecated).
- Use path imports for anything not in the stdlib allowlist.
- `main.ato` should import reusable local wrappers directly from `packages/<name>/<name>.ato`.
- Use `./relative/path.ato` for truly local sibling files, not for canonical wrapper packages under `packages/`.

## 2.8 Traits

Traits attach metadata and behavior to blocks. Use them only for traits that are actually supported by the language/runtime.

```ato
#pragma experiment("TRAITS")
import can_bridge_by_name

module MyModule:
    """
    Requirements:
    - R1: Supply voltage — 3.3V regulated
    """

    # Bridge trait for series-path modules
    trait can_bridge_by_name<input_name="power_in", output_name="power_out">

    # Targeted trait on a specific field
    trait some_field has_part_removed
```

Common traits:

| Trait | Purpose |
|-------|---------|
| `can_bridge_by_name` | Enable `~>` bridge connect through a module's named in/out fields |
| `has_part_removed` | Suppress part picking for non-BOM placeholders |
| `has_single_electric_reference` | Declare shared reference rail for an interface |

## 2.9 Assignments and Overrides

### Parameter assignment

```ato
r.resistance = 10kohm +/- 5%
cap.capacitance = 100nF +/- 20%
ldo.v_out = 3.3V +/- 3%
```

### Special override fields

These field names map to trait behavior:

```ato
r.package = "0402"              # footprint/package constraint
led.lcsc_id = "C2286"           # lock to specific LCSC part
ic.manufacturer = "Texas Instruments"
ic.mpn = "TLV75901PDDR"
i2c.required = True             # mark interface as required
net.override_net_name = "VCC"   # force net name
net.suggest_net_name = "SDA"    # suggest net name
param.default = 0x20            # default value (overridable)
```

### Defaults

Package/module authors set defaults; integrators override with explicit constraints:

```ato
# In the package module:
i2c.address.default = 0x20

# In the integration module:
assert sensor.i2c.address within 0x21 to 0x21
```

## 2.10 For Loops

Requires `FOR_LOOP` pragma. Used for repetitive constraint/wiring patterns, not logic branching.

```ato
#pragma experiment("FOR_LOOP")

# Iterate over a sequence
for cap in decoupling_caps:
    cap.capacitance = 100nF +/- 20%
    cap.package = "0402"

# Iterate with slice
for cap in decoupling_caps[1:]:
    cap.package = "0603"

# Iterate over explicit list of references
for rail in [power_core, power_io, power_analog]:
    assert rail.voltage within 3.3V +/- 10%
```

**Restricted — NOT allowed in loop body:**
- `import` statements
- `new` assignments (create arrays outside the loop, constrain inside)
- `pin` / `signal` declarations
- `trait` statements
- Nested `for` loops

```ato
# Good: create array outside, constrain inside
resistors = new Resistor[8]
for r in resistors:
    r.resistance = 1kohm +/- 20%
    r.package = "0402"

# Bad: creating instances inside loop
for r in resistors:
    x = new Resistor    # NOT ALLOWED
```

## 2.11 Pragmas

Feature gates for experimental constructs. Place at top of file, only include what you use.

```ato
#pragma experiment("BRIDGE_CONNECT")       # enables ~> and <~
#pragma experiment("FOR_LOOP")             # enables for loops
#pragma experiment("TRAITS")               # enables trait statements
#pragma experiment("MODULE_TEMPLATING")    # enables new Type<k=v>
```

Unknown experiment names are errors.

## 2.12 Retype

`->` performs deferred specialization of an existing field to a more specific type:

```ato
module USB2_0TypeCVerticalConnector from USBTypeCConnector_driver:
    connector -> VerticalUSBTypeCConnector_model
```

Use sparingly — only for clear specialization points like swapping a connector variant. Do not use as a general-purpose assignment.

## 2.13 Pin and Signal Declarations

Used inside `component` and `interface` blocks:

```ato
component MyChip:
    pin VCC
    pin GND
    pin 1
    pin "A0"

interface MyBus:
    signal data
    signal clock
```

In practice, you rarely write pin declarations by hand — they come from auto-generated part files.

## 2.14 Not Supported

ato is declarative. Do NOT generate or suggest:

- `if` / `elif` / `else` / `while` / `match`
- Function definitions, lambdas, classes
- `try` / `except` / `finally`
- List comprehensions, dict literals
- Decorators

If a user asks for conditional behavior, express it as constraints and module alternatives.

---

# 3. Stdlib Reference

## 3.1 Interfaces

### `Electrical`

Untyped electrical connection point. Use when you only need net continuity with no reference semantics.

### `ElectricPower`

Two-rail power interface.

| Field | Type | Description |
|-------|------|-------------|
| `hv` | `Electrical` | High-side rail |
| `lv` | `Electrical` | Low-side rail |
| `voltage` | parameter | Rail voltage |
| `max_current` | parameter | Current capacity |
| `max_power` | parameter | Power budget |

Legacy aliases `vcc` and `gnd` exist — prefer `hv`/`lv`.

```ato
power = new ElectricPower
assert power.voltage within 3.3V +/- 5%
```

### `ElectricSignal`

Single signal line with explicit reference power rail. Use for analog or general signals.

| Field | Type | Description |
|-------|------|-------------|
| `line` | `Electrical` | Signal line |
| `reference` | `ElectricPower` | Reference rail |

### `ElectricLogic`

Logic signal (line + reference). Use for GPIOs, digital control, interrupts, reset, enable.

| Field | Type | Description |
|-------|------|-------------|
| `line` | `Electrical` | Signal line |
| `reference` | `ElectricPower` | Reference rail |

**`ElectricLogic` vs `ElectricSignal`**: Use `ElectricLogic` for digital. Use `ElectricSignal` for analog/general.

**Important:** Always connect the `.reference` when crossing module boundaries:

```ato
gpio.reference ~ power
i2c.sda.reference ~ power
```

Missing reference wiring is a common source of bugs.

### `I2C`

Two-wire bus with address and frequency.

| Field | Type | Description |
|-------|------|-------------|
| `scl` | `ElectricLogic` | Clock |
| `sda` | `ElectricLogic` | Data |
| `address` | parameter | Device address |
| `frequency` | parameter | Bus frequency |

```ato
i2c = new I2C
i2c.scl.reference ~ power
i2c.sda.reference ~ power
assert i2c.frequency within 100kHz to 400kHz
```

### `SPI`

3-wire data+clock bus (CS managed separately).

| Field | Type | Description |
|-------|------|-------------|
| `sclk` | `ElectricLogic` | Clock |
| `miso` | `ElectricLogic` | Master In Slave Out |
| `mosi` | `ElectricLogic` | Master Out Slave In |
| `frequency` | parameter | Bus frequency |

### `MultiSPI`

Multi-lane SPI/QSPI style interface.

| Field | Type | Description |
|-------|------|-------------|
| `clock` | `ElectricLogic` | Clock |
| `chip_select` | `ElectricLogic` | Chip select |
| `data[n]` | `ElectricLogic` | Data lanes |

### `UART_Base` and `UART`

`UART_Base` — minimal TX/RX. `UART` — full with flow control (RTS/CTS). `UART` includes `base_uart` sub-field.

### `I2S`

Audio serial bus.

| Field | Type | Description |
|-------|------|-------------|
| `sd` | `ElectricLogic` | Serial data |
| `ws` | `ElectricLogic` | Word select |
| `sck` | `ElectricLogic` | Serial clock |
| `sample_rate` | parameter | Sample rate |
| `bit_depth` | parameter | Bit depth |

### `DifferentialPair`

Paired differential signals with impedance parameter.

| Field | Type | Description |
|-------|------|-------------|
| `p` | `ElectricLogic` | Positive |
| `n` | `ElectricLogic` | Negative |
| `impedance` | parameter | Target impedance |

### `USB2_0_IF` and `USB2_0`

`USB2_0_IF` contains differential data pair (`d`) and bus power (`buspower`). `USB2_0` wraps `usb_if` and is easier for top-level module interfaces.

### Other interfaces

`SWD`, `JTAG`, `Ethernet`, `XtalIF` — available for import, commonly used in package modules.

## 3.2 Components

### `Resistor`

Auto-pickable passive. Key fields:

```ato
r = new Resistor
r.resistance = 10kohm +/- 5%
r.package = "0402"
```

Two unnamed pins accessed via bridge connect or `r.unnamed[0]` / `r.unnamed[1]`.

### `Capacitor`

```ato
cap = new Capacitor
cap.capacitance = 100nF +/- 20%
cap.package = "0402"
```

### `Inductor`

```ato
ind = new Inductor
ind.inductance = 10uH +/- 20%
ind.max_current = 1A
```

### `Diode`

Key fields: `anode`, `cathode`, `forward_voltage`, `max_current`.

### `LED`

Extends Diode behavior. Key fields: `diode.forward_voltage`, `diode.max_current`.

```ato
led = new LED
led.lcsc_id = "C2286"        # lock to specific LED
```

### `Fuse`

Series protection element with bridge capability.

### `ResistorVoltageDivider`

Pre-built voltage divider module with `r_top`, `r_bottom`, and ratio equations.

### `MountingHole`

Standalone mounting hole for mechanical attachment.

### `TestPoint`

Test point for debugging and measurement.

### `NetTie`

Net tie for connecting separate nets on the PCB.

## 3.3 Traits

Traits require `#pragma experiment("TRAITS")` and must be imported.

### Requirements in docstrings

Document design requirements in the owning module's docstring.

```ato
module PowerSupply:
    """
    Requirements:
    - R1: Supply voltage — 3.3V regulated from USB
    """
```

### `can_bridge_by_name`

Enable bridge connect (`~>`) through a module by naming its input and output fields.

```ato
import can_bridge_by_name
trait can_bridge_by_name<input_name="power_in", output_name="power_out">
```

### `has_part_removed`

Suppress part picking. Used for non-BOM placeholders or integration stubs.

```ato
trait some_field has_part_removed
```

### `has_single_electric_reference`

Declare that an interface shares a single reference rail. Used internally by stdlib interfaces.

### Assignment-based trait shortcuts

These field assignments map to traits without needing explicit trait syntax:

- `x.package = "0402"` — package/footprint requirement
- `x.lcsc_id = "C12345"` — lock to LCSC part
- `x.manufacturer = "TI"` — manufacturer constraint
- `x.mpn = "TLV75901PDDR"` — manufacturer part number
- `x.required = True` — mark as externally required
- `x.override_net_name = "VCC"` — force net name
- `x.suggest_net_name = "SDA"` — suggest net name
- `x.default = 0x20` — set default (overridable by downstream constraints)

---

# 4. Patterns and Examples

## 4.1 Interface-first module boundaries

Expose external behavior as interfaces; keep internals private.

```ato
module SensorBoard:
    power = new ElectricPower
    i2c = new I2C

    # Internal blocks
    sensor = new SomeSensor
    pullups = new Resistor[2]

    power ~ sensor.power
    i2c ~ sensor.i2c
```

Avoid exposing internal package pins as public API.

## 4.2 Rail-centric power architecture

Model power as named `ElectricPower` rails and bridge modules between them.

```ato
#pragma experiment("BRIDGE_CONNECT")

module PowerTree:
    vin = new ElectricPower
    vout = new ElectricPower
    fuse = new Fuse
    ldo = new TI_TLV75901

    vin ~> fuse ~> ldo ~> vout
```

## 4.3 Bus spine with localized adapters

Create one bus spine and branch to devices:

```ato
module App:
    i2c_bus = new I2C
    mcu = new MCU
    expander = new NXP_PCF8574
    sensor = new Sensirion_SCD41

    i2c_bus ~ mcu.i2c
    i2c_bus ~ expander.i2c
    i2c_bus ~ sensor.i2c
```

Centralized bus constraints, easy multi-device address management.

## 4.4 Decoupling as local invariant

Each powered IC/module should own its decoupling:

```ato
#pragma experiment("BRIDGE_CONNECT")

decoup = new Capacitor
decoup.capacitance = 100nF +/- 20%
decoup.package = "0402"
power.hv ~> decoup ~> power.lv
```

## 4.5 LED with current-limiting resistor

```ato
#pragma experiment("BRIDGE_CONNECT")
#pragma experiment("TRAITS")

import LED
import Resistor
import ElectricPower
import can_bridge_by_name

module LEDIndicator:
    power = new ElectricPower
    resistor = new Resistor
    led = new LED

    current = 0.5mA to 3mA

    assert (power.voltage - led.diode.forward_voltage) / current is resistor.resistance
    assert current <= led.diode.max_current

    power.hv ~> led ~> resistor ~> power.lv

    signal low ~ power.lv
    signal high ~ power.hv
    trait can_bridge_by_name<input_name="high", output_name="low">
```

## 4.6 Voltage divider with equations

```ato
#pragma experiment("BRIDGE_CONNECT")

import Resistor
import ElectricPower
import ElectricSignal

module VoltageDivider:
    power = new ElectricPower
    output = new ElectricSignal

    r_bottom = new Resistor
    r_top = new Resistor

    v_in: V
    v_out: V
    max_current: A
    r_total: ohm
    ratio: dimensionless

    power.hv ~> r_top ~> output.line ~> r_bottom ~> power.lv

    assert v_out is output.reference.voltage
    assert v_in is power.voltage
    assert r_total is r_top.resistance + r_bottom.resistance
    assert v_out is v_in * r_bottom.resistance / r_total
    assert max_current is v_in / r_total
    assert ratio is r_bottom.resistance / r_total
```

Multiple algebraically equivalent expressions improve solver propagation.

## 4.7 Addressor-driven I2C address configuration

```ato
#pragma experiment("MODULE_TEMPLATING")
#pragma experiment("BRIDGE_CONNECT")
#pragma experiment("FOR_LOOP")

import Addressor
import I2C
import ElectricPower
import Capacitor
import Resistor

module TI_TCA9548A:
    power = new ElectricPower
    i2c = new I2C
    i2cs = new I2C[8]

    assert power.voltage within 1.65V to 5.5V

    addressor = new Addressor<address_bits=3>
    addressor.base = 0x70
    assert addressor.address is i2c.address

    decoupling_caps = new Capacitor[2]
    decoupling_caps[0].capacitance = 100nF +/- 20%
    decoupling_caps[1].capacitance = 2.2uF +/- 20%
    for cap in decoupling_caps:
        power.hv ~> cap ~> power.lv
```

## 4.8 Inline power monitor bridge

```ato
#pragma experiment("TRAITS")
#pragma experiment("BRIDGE_CONNECT")

import ElectricPower
import I2C
import DifferentialPair
import Resistor
import can_bridge_by_name

module TI_INA228:
    power = new ElectricPower
    i2c = new I2C
    power_in = new ElectricPower
    power_out = new ElectricPower

    shunt_input = new DifferentialPair
    shunt = new Resistor
    shunt_input.p.line ~> shunt ~> shunt_input.n.line

    power_in.hv ~> shunt ~> power_out.hv
    power_in.lv ~ power.lv
    power_out.lv ~ power.lv

    trait can_bridge_by_name<input_name="power_in", output_name="power_out">
```

## 4.9 Minimal ESP32 board

```ato
#pragma experiment("FOR_LOOP")
#pragma experiment("BRIDGE_CONNECT")

import ElectricPower

from "atopile/usb-connectors/usb-connectors.ato" import USB2_0TypeCHorizontalConnector
from "atopile/ti-tlv75901/ti-tlv75901.ato" import TI_TLV75901
from "atopile/espressif-esp32-c3/espressif-esp32-c3-mini.ato" import ESP32_C3_MINI_1

module ESP32_MINIMAL:
    micro = new ESP32_C3_MINI_1
    usb_c = new USB2_0TypeCHorizontalConnector
    ldo_3V3 = new TI_TLV75901

    power_3v3 = new ElectricPower

    usb_c.usb.usb_if.buspower ~> ldo_3V3 ~> power_3v3
    power_3v3 ~ micro.power

    ldo_3V3.v_in = 5V +/- 5%
    ldo_3V3.v_out = 3.3V +/- 3%

    usb_c.usb.usb_if ~ micro.usb_if
```

## 4.10 Layout reuse with arrays

```ato
#pragma experiment("FOR_LOOP")
#pragma experiment("BRIDGE_CONNECT")

import Resistor

module Sub:
    r_chain = new Resistor[3]
    for r in r_chain:
        r.resistance = 1kohm +/- 20%
        r.package = "R0402"

    r_chain[0] ~> r_chain[1] ~> r_chain[2]

module Top:
    sub_chains = new Sub[3]

    sub_chains[0].r_chain[2] ~> sub_chains[1].r_chain[0]
    sub_chains[1].r_chain[2] ~> sub_chains[2].r_chain[0]
    sub_chains[2].r_chain[2] ~> sub_chains[0].r_chain[0]
```

## 4.11 Bridgeable data chain

For daisy-chain protocols (addressable LEDs, pass-through interfaces):

```ato
#pragma experiment("TRAITS")
#pragma experiment("BRIDGE_CONNECT")

import ElectricLogic
import can_bridge_by_name

module DataChain:
    data_in = new ElectricLogic
    data_out = new ElectricLogic
    trait can_bridge_by_name<input_name="data_in", output_name="data_out">
```

Enables clean `a ~> chain ~> b` syntax.

## 4.12 Constraint layering

Add constraints from generic to specific:

```ato
# Layer 1: datasheet-safe envelope
assert power.voltage within 2.7V to 5.5V

# Layer 2: system target
assert power.voltage within 3.3V +/- 5%

# Layer 3: manufacturing/package
res.package = "0402"
```

## 4.13 Hybrid auto-pick + locked parts

```ato
#pragma experiment("BRIDGE_CONNECT")
#pragma experiment("FOR_LOOP")

import ElectricPower
import LED
import Resistor

module App:
    power = new ElectricPower

    # Auto-picked by constraints
    current_limiting_resistors = new Resistor[2]
    for resistor in current_limiting_resistors:
        resistor.resistance = 10kohm +/- 20%
        resistor.package = "R0402"

    # Locked to specific parts
    leds = new LED[2]
    leds[0].lcsc_id = "C2286"
    leds[1].manufacturer = "Hubei KENTO Elec"
    leds[1].mpn = "KT-0603R"

    power.hv ~> current_limiting_resistors[0] ~> leds[0] ~> power.lv
    power.hv ~> current_limiting_resistors[1] ~> leds[1] ~> power.lv
```

---

# 5. Troubleshooting

## Feature not enabled (pragma gate)

**Symptom:** Error about experiment not enabled.

**Fix:** Add the required pragma at top of file.

| Construct | Required Pragma |
|-----------|----------------|
| `~>` / `<~` | `BRIDGE_CONNECT` |
| `for` loop | `FOR_LOOP` |
| `trait` statement | `TRAITS` |
| `new Type<k=v>` | `MODULE_TEMPLATING` |

## Invalid import

**Symptom:** `DslImportError` for `import Foo`.

**Fix:** If `Foo` is not stdlib-allowlisted, use a path import:

```ato
from "path/to/foo.ato" import Foo
```

## Missing `new`

**Symptom:** Assignment error.

**Fix:** `r = Resistor` → `r = new Resistor`

## Chained assert

**Symptom:** Semantic error on assert with multiple comparisons.

**Fix:** Split into separate asserts:

```ato
# Bad
assert 1V < x < 5V

# Good
assert x > 1V
assert x < 5V
```

## Unit not found

**Symptom:** `UnitNotFoundError`.

**Fix:** Use known symbols: `V`, `A`, `ohm`, `F`, `Hz`, `W`, `H`, `mm`. Check SI prefix spelling.

## Units not commensurable

**Symptom:** Unit mismatch error in range/tolerance.

**Fix:** Ensure both sides have compatible dimensions:

```ato
# Bad
assert x within 3.3V to 5A

# Good
assert x within 3.3V to 5V
```

## Mixed bridge directions

**Symptom:** Direction error in connect statement.

**Fix:** Use one direction per chain. `a ~> b <~ c` is invalid — rewrite as separate statements.

## Loop body contains forbidden statement

**Symptom:** Invalid statement in for-loop body.

**Fix:** Move `import`, `new`, `pin`, `signal`, `trait`, or nested `for` outside the loop. Create arrays before the loop, constrain inside.

## Overconstrained design (solver contradiction)

**Symptom:** Solver reports contradictory constraints.

**Fix:**
1. Find all constraints on the failing parameter.
2. Convert exact assignments to toleranced/bounded values.
3. Remove redundant contradictory assertions.
4. Check `.default` vs explicit assignment interactions.

## Underconstrained design (weak picks)

**Symptom:** Unstable or poor part selection.

**Fix:**
1. Add core electrical bounds (value + rating).
2. Add package constraints (`package = "0402"`).
3. Lock high-risk parts with `lcsc_id` or `mpn`.

## Missing references on logic/signal buses

**Symptom:** Unexpected interface behavior or unresolved voltage domains.

**Fix:** Wire `.reference` to the correct power rail:

```ato
i2c.scl.reference ~ power
i2c.sda.reference ~ power
gpio.reference ~ power
```

## General repair sequence

When a module has multiple errors, fix in this order:

1. Pragma gates
2. Imports
3. Instance creation (`new`)
4. Connection graph (`~` vs `~>`)
5. References for logic/signal buses
6. Assert operators and structure
7. Units and commensurability
8. Picking/package overrides
9. Over/underconstrained parameters
