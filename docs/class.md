# Class, subclass and replace

## Class and subclass

Like classes in most modern languages, we can subclass and inherit from blocks.

```ato
module SomeModule:
    signal some_signal
    signal gnd
    some_variable = "some value"

module SubclassedModule from SomeModule:
    # inherits all the signals and variables from SomeModule
    # we don't need to declare the signals again,
    # but we will replace the value of some_variable
    some_variable = "some other value"

module Test:
    signal gnd
    # creates an instance of the SubclassedModule
    subclased_module = new SubclassedModule
    # connects the some_signal of the SubclassedModule to the gnd of Test
    subclased_module.gnd ~ gnd
```

**note**: we can subclass a module as a component, but not the other way around. A component is expected to represent a specific component.

This subclassing is also useful for creating typed interfaces:

```ato
interface I2C:
    signal sda
    signal scl

module SomeModule:
    i2c = new I2C

module Test:
    a = new SomeModule
    b = new SomeModule
    a.i2c ~ b.i2c  # connects both sda and scl in one fell swoop
```

## `->` the replace operator

This operator allows you to increase the specificity of a block somewhere.

Take the following example:
1. You want to create a reusable half-bridge module
2. If you spec the FETs within the module, you can't readily reuse the design in other projects with other FETs
3. If you don't declare the FETs at the bottom level it's a PITA to use, since every time you use it you need to remember to slot the FET in the right spot

You want some way to say "we're putting a FET here, but we'll tell you which FET later"

Subclassing is the way you say what a FET is, the replacement operator gives you the later.

```ato
module NFET:
    signal gate
    signal source
    signal drain

module HalfBridge:
    signal high
    signal low
    signal output
    signal high_gate
    signal low_gate

    high_fet = new NFET
    low_fet = new NFET

    # let's pretend we do something useful here like hook it all up

# some time later... perhaps in another file

component SomeNFET from NFET:
    footprint = "TO-220-3_Vertical"
    # this isn't a legit package, but you get the idea

module MotorController:
    a = new HalfBridge
    # ...
    # replace the fets with a SomeNFET
    a.high_fet -> SomeNFET
    a.low_fet -> SomeNFET
```