# Bosch BME280 Temperature, Humidity & Pressure Sensor

This package provides an Atopile driver for the **Bosch BME280** digital environmental sensor (LCSC C?? – replace with actual part number). The device measures temperature, relative humidity, and barometric pressure, communicates via I²C, offers two selectable addresses (0x76 / 0x77), and requires separate core and I/O supplies.

## Usage

```ato
import I2C, ElectricPower
from "packages/bosch-bme280/bme280.ato" import Bosch_BME280

module Top:
    bus = new I2C
    pwr = new ElectricPower
    sensor = new Bosch_BME280

    bus ~ sensor.i2c
    pwr ~ sensor.power_core
    pwr ~ sensor.power_io
```

See the `Usage` module in `usage.ato` for a complete, runnable demo.

## Contributing

Contributions are welcome! Feel free to open issues or pull requests.

## License

This package is provided under the [MIT License](https://opensource.org/license/mit/).
