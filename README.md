<h1 align="center">
    <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://github.com/atopile/atopile/assets/9785003/00f19584-18a2-4b5f-9ce4-1248798974dd">
    <source media="(prefers-color-scheme: light)" src="https://github.com/atopile/atopile/assets/9785003/d38941c1-d7c1-42e6-9b94-a62a0996bc19">
    <img alt="Shows a black logo in light color mode and a white one in dark color mode." src="https://github.com/atopile/atopile/assets/9785003/d38941c1-d7c1-42e6-9b94-a62a0996bc19" width="260">
    </picture>
</h1>

<p align="center">
  <a href="https://pypi.org/project/atopile/"><img alt="PyPI" src="https://img.shields.io/pypi/v/atopile.svg"></a>
  <a href="https://docs.atopile.io/"><img alt="Docs" src="https://img.shields.io/badge/docs-atopile.io-blue"></a>
  <a href="https://packages.atopile.io/"><img alt="Packages" src="https://img.shields.io/badge/packages-registry-brightgreen"></a>
  <a href="https://discord.gg/CRe5xaDBr3"><img alt="Discord" src="https://img.shields.io/badge/Discord-join-5865F2?logo=discord&logoColor=white"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-green"></a>
</p>

## Design circuit boards with code

Write hardware like software. atopile is a language, compiler, and toolchain for electronics—declarative `.ato` files, deep validation, and layout that works natively with KiCad.

<p align="center">
  <img src="assets/tool.jpeg" alt="atopile editor with a project open" width="1152">
</p>

## Why atopile

- Reusable modules instead of starting from scratch every time
- Capture intent with equations directly in your design
- Automatic parametric picking of discrete components

## Install

The easiest way is via the editor extension—it installs and manages `ato` for you:

- VS Code/Cursor extension: https://marketplace.visualstudio.com/items?itemName=atopile.atopile

Advanced setups and CLI installs: https://docs.atopile.io/atopile/guides/install

## Quickstart (2 minutes)

1. Install the extension (link above)

2. In the editor, run “atopile: Open Example” and pick one

3. Press the ▶ in the ato menu bar to build, or run `ato build` from the terminal

4. Open layout when ready

Notes:

- The ato menu bar is in the bottom-left of your VS Code/Cursor window
- KiCad is optional to get started. Without it, you won’t open the PCB, but builds still run and update the `.kicad_pcb`. Install later when you’re ready for layout: https://docs.atopile.io/atopile/quickstart

## How it works

- `ato` is a declarative language for electronics: modules, interfaces, units, tolerances, and assertions
- The compiler solves constraints, picks parts, runs checks, and updates your KiCad layout
- The extension adds language services and one‑click controls
  
Learn more: https://docs.atopile.io/atopile/essentials/1-the-ato-language

### Where atopile fits in

High-level steps:

- Requirements — capture specs with units, tolerances, and assertions
- Component selection — parametric picking, reuse proven modules
- Design capture — `.ato` modules and interfaces compose your system
- Layout — place and route in KiCad
- Checks — run design checks locally or in CI
- Build outputs — BOM, fabrication and assembly data, reports
- PCB fab/assembly — send outputs to your manufacturer

## Examples

- Quickstart walkthrough: https://docs.atopile.io/atopile/quickstart
- Open examples via the editor (“atopile: Open Example”)
- NONOS — Open-source smart speaker https://github.com/atopile/nonos
- AI-Pin — Vibe-coded Humane Pin https://github.com/atopile/ai-pin
- Hyperion — 300K nit display for raves https://github.com/atopile/hyperion

## Packages and parts

- Browse and install modules from the registry: https://packages.atopile.io
- Guide: https://docs.atopile.io/atopile/essentials/4-packages
- Publish your own: https://docs.atopile.io/atopile/guides/publish

## Compatibility

- OS: macOS, Linux, Windows (WSL recommended)
- Recommended editors: VS Code / Cursor
- EDA: KiCad recommended for layout; not required to start

## Contributing and development

- Development setup: https://docs.atopile.io/atopile/guides/development
- Editable install (for working on atopile itself): https://docs.atopile.io/atopile/guides/install#editable-installation-best-for-development
- Run tests:

```sh
pytest -q
```

- Issues and feature requests: https://github.com/atopile/atopile/issues

## Support

- Discord “help” channel: https://discord.gg/CRe5xaDBr3
- Commercial support: hi@atopile.io

## License

MIT. See `LICENSE`.
