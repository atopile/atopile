# SPIN
SPIN is a BLDC motor controller using the SimpleFOC library. Designed as a reference project, hopefully serving as a starting point for your own projects with motor control!

![Slow to Fast HQ](assets/images/slow-to-fast-hq.gif)

## Specs

- 3-phase BLDC nema 17 motor
- 12-24V power supply
- 2A continuous current, 5A peak current
- 14bit magnetic encoder (0.02° resolution)

## Features

- XT30 power connector (x2 for daisy chaining)
- JST-GH 4-pin CAN bus connector (x2 for daisy chaining)
- Stemma/Qwiic I2C connector
- Addressable RGB LEDs for status indication
- USB-C for programming and debugging

## Roadmap

Second version of the board is currently in manufacturing to add CAN bus and I2C communication.

- [x] Power supply bring-up
- [x] Open loop velocity control
- [x] Closed loop current control
- [x] Position control with magnetic encoder
- [ ] CAN bus control (position, velocity, current)
- [ ] CAN bus motion profile
- [ ] I2C communication
- [ ] Enumeration with multiple devices

## Documentation

Interested in building your own SPIN or helping out with the project? Check out the [repo](https://github.com/atopile/spin-servo-drive) and [discord](https://discord.gg/9eazVafH8H) for more information on how to get started!