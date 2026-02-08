# STM32 Auto-Generator for atopile

Automated pipeline that generates high-quality `.ato` component definitions
for STM32 microcontrollers using ST's open pin data and LCSC footprints.

## Results

**28 MCUs generated, 28/28 build-tested successfully** across 12 STM32 families:

| Family | Parts | Description |
|--------|-------|-------------|
| C0 | STM32C011F6P6, STM32C031C6T6 | Entry-level Cortex-M0+ |
| F0 | STM32F030F4P6, STM32F042F6P6, STM32F072CBT6 | Value Cortex-M0 |
| F1 | STM32F103C8T6 | "Blue Pill" Cortex-M3 |
| F3 | STM32F303CCT6 | Mixed-signal Cortex-M4F |
| F4 | STM32F401CCU6, F407VGT6, F411CEU6, F429ZIT6, F446RET6 | High-performance Cortex-M4F |
| F7 | STM32F722RET6, STM32F746ZGT6 | Performance Cortex-M7 |
| G0 | STM32G0B1RET6 | Mainstream Cortex-M0+ |
| G4 | STM32G431CBT6, STM32G474RET6 | High-perf mixed-signal Cortex-M4F |
| H7 | STM32H723ZGT6, STM32H743ZIT6, STM32H750VBT6 | Max-performance Cortex-M7 |
| L0/L1/L4 | STM32L073RZT6, L151CBT6A, L432KCU6, L476RGT6 | Ultra-low-power |
| L5/U5 | STM32L552ZET6, STM32U575ZIT6Q | TrustZone Cortex-M33 |
| WB/WL | STM32WB55RGV6, STM32WLE5JBI6 | Wireless (BLE + LoRa) |

**Stats:**
- 239 KB of generated `.ato` code (8,216 lines)
- 285 decoupling capacitors auto-placed
- ~35 peripheral interfaces per large MCU (I2C, SPI, UART, USB, SWD)
- HSE + LSE crystal interfaces detected on all applicable parts
- 6+ power domains handled (VDD, VDDA, VDDUSB, VCAP, VBAT, VREF+, VDDIO, VLCD, PDR_ON)
- Package sizes: TSSOP20 to LQFP144 (20 to 144 pins)

## What's Generated

Each `.ato` module includes:

1. **Package instantiation** with LCSC footprint (auto-installed via `ato create part`)
2. **Power domains** — VDD, VDDA, VDDUSB, VCAP, VBAT, VREF+ with correct pin mappings
3. **Decoupling capacitors** — sized per VDD pin count, with bulk caps for high-pin parts
4. **Standard interfaces** — SWD, USB (Full-Speed), I2C, SPI, UART with default pin assignments
5. **Crystal interfaces** — HSE and LSE with correct oscillator pin detection
6. **GPIO arrays** — per-port ElectricLogic arrays with full pin-to-package mappings
7. **Documentation** — docstrings with MCU specs, interface-to-index mapping, pin assignments

## How It Works

```
STM32_open_pin_data XML ──┐
                          ├──> stm32_gen.py ──> generated/*.ato
ato create part (LCSC) ───┘
```

1. **Parse** ST's XML pin data for MCU metadata, pin functions, and alternate functions
2. **Install** the LCSC footprint via `ato create part` and parse the generated package `.ato`
3. **Discover** standard interfaces (SWD > USB > I2C > UART > SPI) with priority-based conflict resolution
4. **Analyze** power domains from the *actual* LCSC signal names (handles VDD_1, VDD_VDDA, VDDA_VREFpos, etc.)
5. **Detect** HSE/LSE crystal pins regardless of LCSC naming quirks
6. **Generate** the complete `.ato` module

### Key Design Decision

The generator parses the `ato create part` output to get *actual* LCSC signal names rather than
predicting them from the XML. This handles the wild naming variance across packages:
- `VDD` vs `VDD_1`/`VDD_2` vs `VDD_VDDA`
- `VDDA` vs `VDDA_VREFpos`
- `PH0_OSC_IN` vs `PH0` vs `PF0_OSC_INPF0`
- `PA13` vs `PA13SWDIO`
- `VCAP1` vs `VCAP_1` vs `Vcap_1` vs `VCAP`

## Usage

### Generate a single MCU:
```bash
python stm32_gen.py /path/to/STM32F103C8Tx.xml \
  --mfr-search STMicroelectronics:STM32F103C8T6 \
  -o generated/stm32f103c8t6.ato
```

### Generate the full batch (28 MCUs):
```bash
python batch_generate.py
```

### Build-test all generated files:
```bash
python build_test_all.py
```

## Files

| File | Purpose |
|------|---------|
| `stm32_gen.py` | Core generator (~1000 lines) |
| `batch_generate.py` | Batch generation with curated MCU list |
| `build_test_all.py` | Sequential build-test runner |
| `generated/*.ato` | 28 generated MCU definitions |
| `parts/` | Auto-installed LCSC footprints |

## Dependencies

- Python 3.10+
- atopile CLI (`ato`)
- [STM32_open_pin_data](https://github.com/STMicroelectronics/STM32_open_pin_data) (cloned to `~/projects/`)
