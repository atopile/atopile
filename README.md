<h1 align="center">
    <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://github.com/atopile/atopile/assets/9785003/00f19584-18a2-4b5f-9ce4-1248798974dd">
    <source media="(prefers-color-scheme: light)" src="https://github.com/atopile/atopile/assets/9785003/d38941c1-d7c1-42e6-9b94-a62a0996bc19">
    <img alt="Shows a black logo in light color mode and a white one in dark color mode." src="https://github.com/atopile/atopile/assets/9785003/d38941c1-d7c1-42e6-9b94-a62a0996bc19">
    </picture>
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
<h1 align="center">
    <br>
        <img src="docs/assets/images/code-layout-pcb.png" alt="Logo atopile" title="Logo atopile" />
    <br>
</h1>

## 📖 What Is `atopile`?
`atopile` is a tool to build electronic circuit boards with code.

## 🗣️ Join Us On Discord
What's your story in electronics? What would you like us to build? Come talk on discord.

[![Discord Banner 3](https://discordapp.com/api/guilds/1022538123915300865/widget.png?style=banner2)](https://discord.gg/nr5V3QRUd3)

## ⚡️`ato` Code Examples

### A simple voltage divider
```python
import Resistor, ElectricPower, ElectricSignal

module VoltageDivider:
    """
    A voltage divider using two resistors.

    Connect to the `power` and `output` interfaces
    Configure via:
    - `power.voltage`
    - `output.reference.voltage`
    - `max_current`
    """

    # External interfaces
    power = new ElectricPower
    output = new ElectricSignal

    # Components
    r_bottom = new Resistor
    r_top = new Resistor

    # Variables
    v_in: voltage
    v_out: voltage
    max_current: current
    total_resistance: resistance
    ratio: dimensionless
    r_total: resistance

    # Connections
    power.hv ~ r_top.p1; r_top.p2 ~ output.line
    output.line ~ r_bottom.p1; r_bottom.p2 ~ power.lv

    # Link interface voltages
    assert v_out is output.reference.voltage
    assert v_in is power.voltage

    # Equations - rearranged a few ways to simplify for the solver
    assert r_top.resistance is (v_in / max_current) - r_bottom.resistance
    assert r_bottom.resistance is (v_in / max_current) - r_top.resistance
    assert r_top.resistance is (v_in - v_out) / max_current
    assert r_bottom.resistance is v_out / max_current
    assert r_bottom.resistance is r_total * ratio
    assert r_top.resistance is r_total * (1 - ratio)

    # Calculate outputs
    assert r_total is r_top.resistance + r_bottom.resistance
    assert v_out is v_in * r_bottom.resistance / r_total
    assert v_out is v_in * ratio
    assert max_current is v_in / r_total
    assert ratio is r_bottom.resistance / r_total
```

### Discover Full Projects

Checkout out the [hil test equipment](https://github.com/atopile/hil) or [servo drive project](https://github.com/atopile/spin-servo-drive).

## 🔨 Getting Started

Find our [documentation](https://atopile.io/), [installation video](https://www.youtube.com/watch?v=XqFhFs-FhQ0) and getting started [video](https://www.youtube.com/watch?v=7aeZLlA_VYA).

`atopile` is on pypi.org: https://pypi.org/project/atopile/

### Installation

`atopile` is published to [pypi.org](https://pypi.org/project/atopile/). We recommend installing into an isolated environment, e.g. with `uv`:

```sh
uv tool install atopile
```

Or with `pipx` (requires Python 3.13):
```sh
pipx install atopile
```

## ❓ Why Atopile?

The objective of atopile is to help push forward these paradigms from the software world to hardware, mainly these points:

* **Intelligent Design Capture**: Define hardware specifications like ratios and tolerances in code, enabling precise control and easy reuse of designs.
* **Version Control Integration**: Use git to manage design changes, facilitating collaboration and ensuring each iteration is thoroughly reviewed and validated.
* **Continuous Integration (CI)**: Implement CI to guarantee high-quality, compliant designs with every commit, represented by a green checkmark for assurance.

Describing hardware with code might seem odd at first glance. But once you realize it introduces software development paradigms and toolchains to hardware design, you'll be hooked, just like we've become.

Code can **capture the intelligence** you put into your work. Imagine configuring not the resistance values of a voltage divider, but its ratio and total resistance, all using **physical units** and **tolerances**. You can do this because someone before you described precisely what this module is and described the relationships between the values of the components and the function you care about. Now instead imagine what you can gain from **reusing** a buck design you can merely **configure** the target voltage and ripple of. Now imagine **installing** a [servo drive](https://github.com/atopile/spin-servo-drive) the same way you might numpy.

Version controlling your designs using **git** means you can deeply **validate** and **review** changes a feature at a time, **isolated** from impacting others' work. It means you can detangle your organisation and **collaborate** on an unprecedented scale. We can forgo half-baked "releases" in favor of stamping a simple git-hash on our prototypes, providing an anchor off which to **associate test data** and expectations.

Implementing CI to **test** our work ensures both **high-quality** and **compliance**, all summarised in a green check mark, emboldening teams to target excellence.

## 🔍 Discover what people build

Browse and submit your modules at [packages.atopile.io](https://packages.atopile.io)
