# Basic types & Connections

There's a handful of major types that you'll use in your `.ato` files, falling into two categories: blocks and nodes.

Blocks represent something that can contain other things. They provide an abstraction over their contents. For example, a block could be a power supply chip and all the passive components around it.

Nodes are elements you can connect to.

Block types are:
- `component` - represents exactly one component
- `module` - a collection of components and other modules
- `interface` - walks the line between a block and a node. It's a connectable block that lets you connect multiple nodes at a time

Node types are:
- `pin` - represents a physical pin/pad on a package
- `signal` - represents a logical signal that can be connected to other signals


## Block definition

### Components

Here is an example of a block (in this case, a `component`) created within a file named `resistor.ato`:

```ato
component Resistor:
    signal p1  # declare a signal named "p1"
    p1 ~ pin 1  # connect that "p1" signal with pin 1
    signal p2 ~ pin 2  # declare a signal named "p2" and connect it with pin 2 in one line
    footprint = "R0402"
```

#### Footprints for resistors and capacitors

For convenience, the footprints for resistors and caps can be defined like so

| Package | Resistor footprint | Capacitor footprint |
| :------- | :------: | -------: |
| 01005 | R01005 | C01005 |
| 0201 | R0201 | C0201 |
| 0402 | R0402 | C0402 |
| 0603 | R0603 | C0603 |
| 0805 | R0805 | C0805 |
| 1206 |       | C1206 |

### Modules

Here is an example of a `module` definition, in this case a resistor divider:

```python
from "generics/resistors.ato" import Resistor

module YourModule:
    signal top
    signal out
    signal bottom

    r_top = new Resistor
    r_top.footprint = "R0402"
    r_bottom = new Resistor
    r_bottom.footprint = "R0402"

    top ~ r_top.p1; r_top.p2 ~ out
    out ~ r_bottom.p1; r_bottom.p2 ~ bottom
```

A module can contain an arbitrary amount of components, modules, signals, and interface instances.

### Interfaces

Here is an example of an `interface` definition; in this case, a CAN interface

```
interface YourInterface:
    signal CANH
    signal CANL
```

An interface can contain an arbitrary amount of signals.

Interfaces can be connected together with the `~` operator like so:

```
interface_1 = new YourInterface
interface_2 = new YourInterface

interface_1 ~ interface_2
```

Two interfaces can be connected as long as they contain the same signals.

## Node definition

### Signal definition

Signals can be useful as they allow you to name a connection point used throughout your design. Here is an example with a ground signal:

```ato
signal gnd
```

Signals can be connected in the following way:

```ato
signal enable_pin
signal vcc
enable_pin ~ vcc
```

### Pin definition

Pins can be defined in a similar way to signals. Pins are used specifically within components to tie your signals back to your footprints. The pin should have the same name as the copper pads in your footprint.

We usually recommend creating a signal within your component and tying it to your pin. That gives you a meaningful signal to connect to instead of an ephemeral pin. For example:

```
signal vcc ~ pin 1
```
