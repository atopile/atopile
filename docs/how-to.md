# How-Tos

## Pin Configuration

Say you've got `SomeIC`, which has two signals (`configure_me` and `configure_me_too`) to set its I2C address.
You want to write a module which supports all these addresses in a simple manner.

You can do something like this!

```
module SomeIC:
    signal configure_me ~ config.bit_0
    signal configure_me_too ~ config.bit_1
    # etc... (do power and what not as required)

    # Replace me!
    config = new _ConfigBase
    # You could also enforce this with an
    #   assertion if you really wanted to


module _ConfigBase:  # <--- Prefixed with the underscore implies private
    """Must be replaced with an actual configuration."""
    power = new Power
    signal bit_0
    signal bit_1


module Config0x70 from _ConfigBase:
    """For selecting address 0x70"""
    bit_0 ~ power.gnd
    bit_1 ~ power.gnd


module Config0x71 from _ConfigBase:
    """For selecting address 0x71"""
    bit_0 ~ power.vdd  # <--- see this bit is now high?
    bit_1 ~ power.gnd


# etc...
```

Then, when you go to use `SomeIC` you can just do:

```

some_ic = new SomeIC
some_ic.config -> Config0x70
```


## Something not here?

If you're looking for a how-to that isn't here, please ask us on Discord or open an issue on GitHub!
