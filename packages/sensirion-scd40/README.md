# Sensirion SCD40 CO₂ Sensor

This package provides an Atopile driver for the **Sensirion SCD40-D-R2** photoacoustic CO₂ sensor (LCSC C3659421). The sensor communicates over I²C and operates from a single 1.65 V – 3.6 V supply.

## Usage

```ato
import I2C, ElectricPower
from "packages/sensirion-scd40/scd40.ato" import Sensirion_SCD40, Example

# Minimal wiring example
module Top:
    bus = new I2C
    pwr = new ElectricPower
    sensor = new Sensirion_SCD40

    bus ~ sensor.i2c
    pwr ~ sensor.power
```

See the `Example` module in `scd40.ato` for a complete, runnable demo.

## Contributing

Contributions are welcome! Feel free to open issues or pull requests.

## License

This package is provided under the [MIT License](https://opensource.org/license/mit/).
