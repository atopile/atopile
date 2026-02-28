---
name: ato-language
description: "Reference for the `.ato` declarative DSL: type system, connection semantics, constraint model, and standard library. Use when authoring or reviewing `.ato` code."
---

# The ato language

ato is a **declarative, constraint-based DSL** for describing electronic circuits. There is no control flow, no mutation, and no execution order — you declare _what_ a circuit is, and the compiler + solver resolve it into a valid design.

## Quick Start

A minimal complete `.ato` file:

```ato
#pragma experiment("BRIDGE_CONNECT")

import Resistor
import ElectricPower
import Capacitor

module PowerFilter:
    """A simple decoupled power input with a pull-down resistor."""
    power = new ElectricPower
    decoupling_capacitor = new Capacitor
    pulldown_resistor = new Resistor

    power.hv ~> decoupling_capacitor ~> power.lv
    power.hv ~> pulldown_resistor ~> power.lv

    decoupling_capacitor.capacitance = 100nF +/- 20%
    pulldown_resistor.resistance = 100kohm +/- 5%
    assert power.voltage within 3.0V to 3.6V
```

Validate with `ato build` from the package directory.

## Core Concepts

### 1. Everything is a Node in a Graph

Every entity (a resistor, a power rail, an I2C bus, a voltage parameter) is a **node** in a typed graph. Nodes relate to each other through **edges**: composition (parent–child), connection (same-net), and traits (behavioral metadata). The `.ato` language is a surface syntax for constructing this graph declaratively.

### 2. Three Block Types

ato has exactly three ways to define a new type:

| Keyword     | Semantics                                            | Typical Use                 |
| ----------- | ---------------------------------------------------- | --------------------------- |
| `module`    | A design unit that contains children and connections | Circuit blocks, subsystems  |
| `interface` | A connectable boundary; can be wired with `~`        | Buses, power rails, signals |
| `component` | A physical part with footprint/symbol                | Vendor ICs, connectors      |

All three compile to graph nodes. The distinction controls which **traits** the compiler attaches (`is_module`, `is_interface`) and what operations are legal (by convention, interfaces appear on both sides of `~`).

Inheritance uses `from`:

```ato
module MyRegulator from Regulator:
    pass
```

### 3. Composition — Children and Instantiation

Types contain children. Inside a block body, `new` instantiates a child:

```ato
module Board:
    power = new ElectricPower      # interface child
    sensor = new BME280            # module child
    caps = new Capacitor[4]        # array of 4 capacitors
```

Children are accessed via **dot-notation**: `sensor.power.voltage`, `caps[0].capacitance`.

### 4. Connection — Declaring Electrical Identity

The **wire operator `~`** declares that two interfaces _are the same net/bus_. It is bidirectional and requires matching types:

```ato
power_3v3 ~ sensor.power          # ElectricPower ~ ElectricPower
i2c_bus ~ sensor.i2c              # I2C ~ I2C
```

The **bridge operator `~>`** (requires `#pragma experiment("BRIDGE_CONNECT")`) inserts a component in series. The component must carry the `can_bridge` trait which defines its in/out mapping:

```ato
power_5v ~> regulator ~> power_3v3
i2c.scl.line ~> pullup ~> power.hv
```

### 5. Constraints — Physical Quantities and Assertions

Values in ato carry **units** and **tolerances**. The solver uses these to select real parts.

**Assignment** binds a value to a parameter:

```ato
power.voltage = 3.3V +/- 5%
resistor.resistance = 10kohm +/- 10%
i2c.frequency = 400kHz
i2c.address = 0x48
```

**Assertions** declare constraints the solver must satisfy:

```ato
assert power.voltage within 3.0V to 3.6V
assert i2c.frequency <= 400kHz
assert sensor.i2c.address is 0x50
```

Three value forms exist:

- **Exact**: `3.3V`
- **Bilateral tolerance**: `10kohm +/- 5%`
- **Bounded range**: `3.0V to 3.6V`

### 6. Traits — Behavioral Metadata

Traits attach capabilities or metadata to nodes. They are not children — they use trait edges in the graph.

```ato
#pragma experiment("TRAITS")

import has_part_removed
import is_atomic_part

module Placeholder:
    trait has_part_removed          # mark as non-physical placeholder
    trait is_atomic_part            # user-defined part with footprint
```

Key built-in traits:

| Trait                   | Effect                                                           |
| ----------------------- | ---------------------------------------------------------------- |
| `can_bridge`            | Enables use with `~>` operator (defines in/out pin mapping)      |
| `has_part_removed`      | No physical part placed (symbolic node)                          |
| `is_atomic_part`        | User-defined part with `manufacturer`, `partnumber`, `footprint` |
| `has_datasheet`         | Attaches a datasheet reference                                   |
| `has_designator_prefix` | Sets PCB designator (R, C, U, etc.)                              |

### 7. Import System

**Bare imports** resolve to standard library types (1 line per import):

```ato
import ElectricPower
import I2C
import Resistor
```

**Path imports** resolve to types defined in other `.ato` files (1 line per import):

```ato
from "atopile/vendor-part/vendor-part.ato" import Vendor_Part
```

### 8. Pragma Feature Flags

Experimental syntax is gated behind pragmas (file top, before imports):

```ato
#pragma experiment("BRIDGE_CONNECT")     # ~> operator
#pragma experiment("FOR_LOOP")           # for loops
#pragma experiment("TRAITS")             # trait keyword
#pragma experiment("MODULE_TEMPLATING")  # new Foo<p=v>
#pragma experiment("INSTANCE_TRAITS")    # traits on instances
```

Using gated syntax without the pragma is a compile error.

## Statement Reference

Every statement inside a block body is one of:

| Statement | Syntax                              | Purpose                                |
| --------- | ----------------------------------- | -------------------------------------- |
| `assign`  | `name = value` or `name = new Type` | Bind a value or instantiate a child    |
| `connect` | `a ~ b`                             | Wire two interfaces together           |
| `bridge`  | `a ~> b ~> c`                       | Insert bridgeable components in series |
| `assert`  | `assert expr <op> expr`             | Declare a constraint                   |
| `retype`  | `name -> NewType`                   | Replace an inherited child's type      |
| `pin`     | `pin VCC`                           | Declare a physical pin                 |
| `signal`  | `signal reset`                      | Declare an electrical signal           |
| `trait`   | `trait TraitName`                   | Attach a trait                         |
| `import`  | `import Type`                       | Import a type                          |
| `for`     | `for x in arr:`                     | Iterate over an array (pragma-gated)   |
| `string`  | `"""..."""`                         | Documentation string                   |
| `pass`    | `pass`                              | Empty placeholder                      |

Statements within a block are **order-independent** — the compiler resolves the full graph, not a sequence of operations.

## Type System

### Interfaces (connectable with `~` or `~>`)

| Type                                                          | Children / Parameters                                    | Purpose                              |
| ------------------------------------------------------------- | -------------------------------------------------------- | ------------------------------------ |
| `Electrical`                                                  | _(single node)_                                          | Raw electrical connection point      |
| `ElectricPower`                                               | `.hv`, `.lv` (Electrical); `.voltage`, `.max_current`    | Power rails                          |
| `ElectricLogic`                                               | `.line` (Electrical), `.reference` (ElectricPower)       | Digital signals with voltage context |
| `ElectricSignal`                                              | `.line` (Electrical), `.reference` (ElectricPower)       | Analog signals                       |
| `I2C`                                                         | `.scl`, `.sda` (ElectricLogic); `.frequency`, `.address` | I2C bus                              |
| `SPI`                                                         | `.sclk`, `.mosi`, `.miso` (ElectricLogic); `.frequency`  | SPI bus                              |
| `UART` / `UART_Base`                                          | `.tx`, `.rx` (ElectricLogic); flow control lines         | Serial                               |
| `I2S`                                                         | audio data bus lines                                     | Digital audio                        |
| `DifferentialPair`                                            | `.p`, `.n`                                               | Differential signals                 |
| `USB2_0` / `USB3` / `USB2_0_IF`                               | USB data + power                                         | USB interfaces                       |
| `CAN_TTL`                                                     | CAN bus lines                                            | CAN bus                              |
| `SWD` / `JTAG`                                                | debug lines                                              | Debug interfaces                     |
| `Ethernet` / `HDMI` / `RS232` / `PDM` / `XtalIF` / `MultiSPI` | protocol-specific                                        | Other protocols                      |

### Modules (instantiable with `new`)

| Type                                | Children / Parameters                                                                  | Designator |
| ----------------------------------- | -------------------------------------------------------------------------------------- | ---------- |
| `Resistor`                          | `.unnamed[0..1]`; `.resistance`, `.max_power`                                          | R          |
| `Capacitor`                         | `.unnamed[0..1]`, `.power`; `.capacitance`, `.max_voltage`, `.temperature_coefficient` | C          |
| `CapacitorPolarized`                | polarized variant of Capacitor                                                         | C          |
| `Inductor`                          | `.unnamed[0..1]`; `.inductance`                                                        | L          |
| `Fuse`                              | `.unnamed[0..1]`; `.trip_current`, `.fuse_type`                                        | F          |
| `Diode`                             | `.anode`, `.cathode`; `.forward_voltage`, `.current`                                   | D          |
| `LED`                               | `.diode`; `.brightness`, `.color`                                                      | D          |
| `MOSFET`                            | `.source`, `.gate`, `.drain`; `.channel_type`, `.gate_source_threshold_voltage`        | Q          |
| `BJT`                               | `.emitter`, `.base`, `.collector`; `.doping_type`                                      | Q          |
| `Regulator` / `AdjustableRegulator` | `.power_in`, `.power_out`                                                              | —          |
| `Crystal`                           | `.unnamed[0..1]`, `.gnd`; `.frequency`, `.load_capacitance`                            | XTAL       |
| `Crystal_Oscillator`                | oscillator module                                                                      | —          |
| `ResistorVoltageDivider`            | voltage divider circuit                                                                | —          |
| `FilterElectricalRC`                | RC filter                                                                              | —          |
| `Net`                               | `.part_of` (Electrical)                                                                | —          |
| `TestPoint`                         | `.contact`; `.pad_size`, `.pad_type`                                                   | TP         |
| `MountingHole` / `NetTie`           | mechanical                                                                             | —          |
| `SPIFlash`                          | SPI flash memory                                                                       | —          |

### Traits (attachable with `trait`)

`has_part_removed`, `is_atomic_part`, `can_bridge`, `can_bridge_by_name`, `has_datasheet`, `has_designator_prefix`, `has_doc_string`, `has_net_name_affix`, `has_net_name_suggestion`, `has_package_requirements`, `has_single_electric_reference`, `is_auto_generated`, `requires_external_usage`

## Units and Literals

**SI-prefixed units**: `V`, `mV` | `A`, `mA` | `ohm`, `kohm`, `Mohm` | `F`, `uF`, `nF`, `pF` | `Hz`, `kHz`, `MHz`, `GHz` | `s`, `ms` | `W`, `mW`

**Number formats**: decimal (`3.3`), scientific (`1e-6`), hex (`0x48`), binary (`0b1010`), underscore-separated (`1_000_000`)

**Booleans**: `True`, `False`

## Invariants

1. **Type-safe connections**: `~` and `~>` should connect matching interface types. `ElectricPower ~ I2C` is a type mismatch (enforcement is being strengthened).
2. **Pragma gates syntax**: using `~>`, `for`, `trait`, or `<>` without the matching pragma is a compile error.
3. **Tolerances on passives**: `resistance = 10kohm` (zero tolerance) matches no real parts. Always use `+/- N%`.
4. **ElectricLogic needs a reference**: logic signals require a power reference for voltage context. Set `signal.reference ~ power_rail`.
5. **Order independence**: statements within a block are not sequentially executed. The solver resolves the full graph.
6. **No procedural logic**: no `if`, `while`, `return`, functions, classes, or exceptions.
