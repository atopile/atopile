# Sensirion SHT31-DIS-B2.5kS Temperature & Humidity Sensor

This package provides an Atopile driver for the **Sensirion SHT31-DIS-B2.5kS** digital temperature and humidity sensor (LCSC C80862). The sensor communicates via I²C, supports two selectable addresses (0x44 / 0x45), and operates from a single 2.4 V – 5.5 V supply.

## Usage

```ato
import I2C, ElectricPower
from "packages/sensirion-sht31/sht31.ato" import SHT31_driver, Example

module Top:
    bus = new I2C
    pwr = new ElectricPower
    sensor = new SHT31_driver

    bus ~ sensor.i2c
    pwr ~ sensor.power
```

See the `Example` module in `sht31.ato` for a complete, runnable demo.

## Contributing

Contributions are welcome! Feel free to open issues or pull requests.

## License

This package is provided under the [MIT License](https://opensource.org/license/mit/).
