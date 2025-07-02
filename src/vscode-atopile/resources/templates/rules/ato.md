# Ato language features

## experimental features

Enable with `#pragma experiment("BRIDGE_CONNECT")`
BRIDGE_CONNECT: enables `p1 ~> resistor ~> p2` syntax
FOR_LOOP: enables `for item in container: pass` syntax
TRAITS: enables `trait trait_name` syntax
MODULE_TEMPLATING: enables `new MyComponent<param=literal>` syntax

## modules, interfaces, parameters, traits

A block is either a module, interface or component.
Components are just modules for code-as-data.
Interfaces describe a connectable interface (e.g Electrical, ElectricPower, I2C, etc).
A module is a block that can be instantiated.
Think of it as the ato equivalent of a class.
Parameters are variables for numbers and they work with constraints.
E.g `resistance: ohm` is a parameter.
Constrain with `assert resistance within 10kohm +/- 10%`.
It's very important to use toleranced values for parameters.
If you constrain a resistor.resistance to 10kohm there won't be a single part found because that's a tolerance of 0%.

Traits mark a module to have some kind of functionality that can be used in other modules.
E.g `trait has_designator_prefix` is the way to mark a module to have a specific designator prefix that will be used in the designator field in the footprint.

## connecting

You can only connect interfaces of the same type.
`resistor0.unnamed[0] ~ resistor0.unnamed[0]` is the way to connect two resistors in series.
If a module has the `can_bridge` trait you can use the sperm operator `~>` to bridge the module.
`led.anode ~> resistor ~> power.hv` connects the anode in series with the resistor and then the resistor in series with the high voltage power supply.

## for loop syntax

`for item in container: pass` is the way to iterate over a container.

# Ato CLI

## How to run

You run ato commands through the MCP tool.

## Packages

Packages can be found on the ato registry.
To install a package you need to run `ato add <PACKAGE_NAME>`.
e.g `ato install atopile/addressable-leds`
And then can be imported with `from "atopile/addressable-leds/sk6805-ec20.ato" import SK6805_EC20_driver`.
And used like this:

```ato
module MyModule:
    led = new SK6805_EC20_driver
```

## Footprints & Part picking

Footprint selection is done through the part choice (`ato create part` auto-generates ato code for the part).
The `pin` keyword is used to build footprint pinmaps so avoid using it outside of `component` blocks.
Preferrably use `Electrical` interface for electrical interfaces.
A lot of times it's actually `ElectricLogic` for things like GPIOs etc or `ElectricPower` for power supplies.

Passive modules (Resistors, Capacitors) are picked automatically by the constraints on their parameters.
To constrain the package do e.g `package = "0402"`.
To explictly pick a part for a module use `lcsc = "<LCSC_PART_NUMBER>"`.
