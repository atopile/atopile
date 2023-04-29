# Language Example

```ato
from "i2c" import I2C;
from "atopile.org/example/SomeDevice" import SomeDevice;

def SomeDevice() {
    pin vcc;
    pin gnd;

    package {
        pin 1;
        pin 2;
        pin 3;
        pin 4;
    }

    vcc ~ package.1;
    gnd ~ package.2;

    def SomeI2CController() {
        i2c = I2C();
        i2c.sda ~ package.3;
        i2c.scl ~ package.4;
        i2c.gnd ~ gnd;
    }
}
```
