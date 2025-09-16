# LED Badge Build Guide

## What We're Building

A wearable LED badge with a 10×10 RGB LED matrix (100 LEDs total) that can display animations, text, and graphics. The badge includes audio input for sound-reactive effects, motion sensing for gesture control, and USB-C connectivity for programming and charging.

## Core Features

- **Visual Display**: 10×10 addressable LED matrix for animations and text
- **Audio Input**: Digital microphone for sound-reactive visuals
- **Motion Sensing**: IMU for gesture detection and orientation
- **Connectivity**: USB-C for programming and power
- **Portable**: Battery-powered with integrated charging

## Required Components

### Main Components

- **ESP32-C3 microcontroller module** - Brain of the device (WiFi/Bluetooth capable)
- **100x SK6805-EC20 addressable LEDs** - Or similar WS2812B-compatible RGB LEDs
- **I2S digital microphone** - Any 3.3V I2S microphone (TDK ICS-43434 recommended)
- **6-axis IMU** - Accelerometer + gyroscope, I2C interface (ST LSM6DS3 or similar)
- **USB-C connector** - For programming and charging

### Power System

- **300mAh Li-Po battery** - 3.7V rechargeable battery
- **Battery charger IC** - Linear charger with power path (BQ25185 or equivalent)
- **Buck-boost converter** - 3.3V regulator (TPS63020 or similar)

### Supporting Components

- **Pull-up resistors**: 2x 4.7kΩ (for I2C), 1x 10kΩ (for buck-boost enable)
- **Passive components**: Capacitors and resistors as needed per IC datasheets

## Key Connections

- **LED data**: GPIO pin 8 → LED matrix data input
- **I2S audio**: GPIO pins 3/4/5 → microphone (WS/SCK/SD)
- **I2C**: SDA/SCL → IMU (with 4.7kΩ pull-ups to 3.3V)
- **USB**: D+/D- → ESP32-C3 USB interface
- **Power**: USB 5V → Charger → Battery/System → Buck-boost → 3.3V rail

## Power Requirements

- **Input**: 5V from USB-C (500mA max)
- **Battery**: 300mAh Li-Po (3.0V-4.2V range)
- **System**: 3.3V regulated output for all components
- **Charging**: ~150mA charge rate (C/2 for battery longevity)

## Development Platform

- **PlatformIO** with ESP32-C3 target
- **Programming**: C/C++ firmware
- **Features**: LED control, I2S audio, I2C sensors, USB communication

---

_This requirements document serves as the functional specification for recreating the LED Badge design. Implementation should follow these requirements while allowing for component substitutions that meet or exceed the specified performance criteria._
