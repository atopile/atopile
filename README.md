<h1 align="center">
    <br>
        <img src="docs/assets/logo-with-text.png" alt="Logo atopile" title="Logo atopile" />
    <br>
</h1>

<div align="center">
    <a href="#">
        <img src="https://img.shields.io/pypi/v/atopile.svg" alt="Version" style="vertical-align:top; margin:6px 4px">
    </a>
    <a href="#">
        <img src="https://img.shields.io/github/license/atopile/atopile.svg" alt="License" style="vertical-align:top; margin:6px 4px">
    </a>
    <a href="#">
        <img src="https://github.com/atopile/atopile/actions/workflows/ci.yml/badge.svg" alt="Build status" style="vertical-align:top; margin:6px 4px">
    </a>
</div>

Build elecronic circuit boards from code.

<h1 align="center">
    <br>
        <img src="docs/assets/images/code-layout-pcb.png" alt="Logo atopile" title="Logo atopile" />
    <br>
</h1>

## 💡Examples

### Votlage divider
```ato
import Resistor from "generics/resistors.ato"

module VoltageDivider:
    signal top
    signal out
    signal bottom

    r_top = new Resistor
    r_top.footprint = "R0402"
    r_top.value = 100kohm +/- 10%

    r_bottom = new Resistor
    r_bottom.footprint = "R0402"
    r_top.value = 200kohm +/- 10%

    top ~ r_top.p1; r_top.p2 ~ out
    out ~ r_bottom.p1; r_bottom.p2 ~ bottom
```

### RP2040 Blinky Circuit
```ato
import RP2040Kit from "rp2040/rp2040_kit.ato"
import LEDIndicator from "generics/leds.ato"
import LDOReg3V3 from "regulators/regulators.ato"
import USBCConn from "usb-connectors/usb-connectors.ato"

module Blinky:
    micro_controller = new RP2040Kit
    led_indicator = new LEDIndicator
    voltage_regulator = new LDOReg3V3
    usb_c_connector = new USBCConn

    usb_c_connector.power ~ voltage_regulator.power_in
    voltage_regulator.power_out ~ micro_controller.power
    micro_controller.gpio13 ~ led_indicator.input
    micro_controller.power.gnd ~ led_indicator.gnd

    led_indicator.resistor.value = 100ohm +/- 10%
```

## 🔨 Getting started

Find our [documentation](https://atopile.io/getting-started/) and getting started [video](https://www.youtube.com/watch?v=7aeZLlA_VYA).

## ❓ Why atopile?

Describing hardware with code might seem odd at first glance. But once you realize it introduces software development paradigms and toolchains to hardware design, you'll be hooked, just like we've become.

Code can **capture the intelligence** you put into your work. Imagine configuring not the resistance values of a voltage divider, but its ratio and total resistance, all using **physcial units** and **tolerances**. You can do this because someone before you described precisely what this module is and described the relationships between the values of the components and the function you care about. Now instead imagine what you can gain from **reusing** a buck design you can merely **configure** the target voltage and ripple of. Now imagine **installing** a [servo drive](https://github.com/atopile/spin-servo-drive) the same way you might numpy.

Version controlling your designs using **git** means you can deeply **validate** and **review** changes a feature at a time, **isolated** from impacting others' work. It means you can detangle your organisation and **collaborate** on an unprecedented scale. We can forgo half-baked "releases" in favor of stamping a simple git-hash on our prototypes, providing an anchor off which to **associate test data** and expectations.

Implementing CI to **test** our work ensures both **high-quality** and **compliance**, all summarised in a green check mark, emboldening teams to target excellence.


## Development
### Prerequisites / Installation

You'll need >= `python3.11` and `pip` (Use `brew`).

I'd strongly recommend developing within a `venv`

Since we'll be using this `venv` for both work within this tool directory and whatever projects you're using it on, I'd recommend creating something along the lines of an `atopile-workspace` or `ato-ws` directory somewhere, and then creating a `venv` in there. This means if you do something like a `git clean -xdf` to remove crud, you won't blow away your `venv` with it.

If you decide to follow this, you'll end up with something like this:

```
atopile-workspace
├── .venv --> your virtual environment
├── atopile --> this repo
├── atopile.code-workspace --> vscode workspace file
└── bike-light --> project using atopile
```

Clone this repo.

Wherever you stick the `venv`, you can create the venv with  `python3.11 -m venv .venv` and then `source .venv/bin/activate`

For cli development (so practically all the time) : `pip install -e ."[dev,test,docs]"`

You'll need `npm` for front-end development (`brew install node`).

For any front-end development, you'll also need to install the front-end dependencies: `npm install`


## Syntax highlighting is pretty nice...

You can download the extension from CI here:

![download-artifacts](docs/images/download-artifacts.png)

Then, from your PC `code --install-extension path/to/atopile-*.vsix`
