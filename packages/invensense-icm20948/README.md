# TDK InvenSense ICM-20948 9-Axis IMU

TDK InvenSense’s ICM-20948 integrates a 3-axis gyroscope, 3-axis accelerometer, and 3-axis magnetometer, delivering a full 9-axis motion-tracking solution in a compact 3 × 3 mm QFN-24 package. This package provides an ato driver that exposes power rails and an I²C bus interface, making it easy to drop the sensor into your design.

## Usage

```ato
#pragma experiment("FOR_LOOP")

import I2C
import ElectricPower
from "packages/invensense-icm20948/icm20948.ato" import Invensense_ICM20948

imu = new Invensense_ICM20948

# Shared rails
power = new ElectricPower
i2c = new I2C

# Connect sensor
imu.power_core ~ power
imu.power_io ~ power
imu.i2c ~ i2c
```

The driver automatically handles:

- Required decoupling capacitors
- Pull-up on **nCS** to select I²C mode
- I²C address selection via **SDO/AD0** (default = 0x68)

## Contributing

Improvements and bug fixes are welcome! Please open an issue or pull request on the [packages repo](https://github.com/atopile/packages).

## License

This atopile package is provided under the [MIT License](https://opensource.org/license/mit/).
