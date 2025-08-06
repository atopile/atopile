Package generation process:

Review structure of other pacakges.

1. Create new Directory in 'packages/packages' with naming convention '<vendor>-<device>' eg 'adi-adau145x'
2. create an ato.yaml file in the new directory with the following content:

```yaml
requires-atopile: '^0.9.0'

paths:
    src: '.'
    layout: ./layouts

builds:
    default:
        entry: <device>.ato:<device>_driver
    example:
        entry: <device>.ato:Example
```

3. Create part using tool call 'search_and_install_jlcpcb_part'
4. Import the part into the <device>.ato file
5. Read the datasheet for the device
6. Find common interfaces in the part eg I2C, I2S, SPI, Power

7. Create interfaces and connect them

power interfaces:
power*<name> = new ElectricPower
power*<name>.required = True # If critical to the device
assert power\*<name>.voltage within <minimum*operating_voltage>V to <maximum_operating_voltage>V
power*<name>.vcc ~ <device>.<vcc pin>
power\_<name>.gnd ~ <device>.<gnd pin>

i2c interfaces:
i2c = new I2C
i2c.scl.line ~ <device>.<i2c scl pin>
i2c.sda.line ~ <device>.<i2c sda pin>

spi interfaces:
spi = new SPI
spi.sclk.line ~ <device>.<spi sclk pin>
spi.mosi.line ~ <device>.<spi mosi pin>
spi.miso.line ~ <device>.<spi miso pin>

8. Add decoupling capacitors

looking at the datasheet, determine the required decoupling capacitors

eg: 2x 100nF 0402:

power_3v3 = new ElectricPower

# Decoupling power_3v3

power_3v3_caps = new Capacitor[2]
for capacitor in power_3v3_caps:
capacitor.capacitance = 100nF +/- 20%
capacitor.package = "0402"
power_3v3.hv ~> capacitor ~> power_3v3.lv

9. If device has pin configurable i2c addresses

If format is: <n x fixed address bits><m x pin configured address bits>
use addressor module:

- Use `Addressor<address_bits=N>` where **N = number of address pins**.
- Connect each `address_lines[i].line` to the corresponding pin, and its `.reference` to a local power rail.
- Set `addressor.base` to the lowest possible address and `assert addressor.address is i2c.address`.

10. Create a README.md

# <Manufacturer> <Manufacturer part number> <Short description>

## Usage

```ato
<copy in example>

```

## Contributing

Contributions to this package are welcome via pull requests on the GitHub repository.

## License

This atopile package is provided under the [MIT License](https://opensource.org/license/mit/).

11. Connect high level interfaces directly in example:

eg:

i2c = new I2C
power = new ElectricPower
sensor = new Sensor

i2c ~ sensor.i2c
power ~ sensor.power_3v3

# Additional Notes & Gotchas (generic)

- Multi-rail devices (VDD / VDDIO, AVDD / DVDD, etc.)

    - Model separate `ElectricPower` interfaces for each rail (e.g. `power_core`, `power_io`).
    - Mark each `.required = True` if the device cannot function without it, and add voltage assertions per datasheet.

- Optional interfaces (SPI vs I²C)

    - If the device supports multiple buses, pick one for the initial driver. Leave unused bus pins as `ElectricLogic` lines or expose a second interface module later.

- Decoupling guidance

    - If the datasheet shows multiple caps, model the **minimum required** set so the build passes; you can refine values/packages later.

- File / directory layout recap
    - `<vendor>-<device>/` – package root
    - `ato.yaml` – build manifest (include `default` **and** `example` targets)
    - `<device>.ato` – driver + optional example module
    - `parts/<MANUFACTURER_PARTNO>/` – atomic part + footprint/symbol/step files

These tips should prevent common "footprint not found", "pin X missing", and build-time path errors when you add new devices.
