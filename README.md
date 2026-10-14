<h1 align="center">
    <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://github.com/atopile/atopile/assets/9785003/00f19584-18a2-4b5f-9ce4-1248798974dd">
    <source media="(prefers-color-scheme: light)" src="https://github.com/atopile/atopile/assets/9785003/d38941c1-d7c1-42e6-9b94-a62a0996bc19">
    <img alt="Shows a black logo in light color mode and a white one in dark color mode." src="https://github.com/atopile/atopile/assets/9785003/d38941c1-d7c1-42e6-9b94-a62a0996bc19" width="260">
    </picture>
</h1>

<p align="center">
  <a href="https://atopile.io"><img alt="Get started" src="https://img.shields.io/badge/get_started-atopile.io-brightgreen"></a>
  <a href="https://docs.atopile.io/"><img alt="Docs" src="https://img.shields.io/badge/docs-atopile.io-blue"></a>
  <a href="https://discord.gg/CRe5xaDBr3"><img alt="Discord" src="https://img.shields.io/badge/Discord-join-5865F2?logo=discord&logoColor=white"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-green"></a>
</p>

## Design circuit boards with code

Write hardware like software. atopile is a language, compiler, and toolchain for electronics—declarative `.ato` files, deep validation, and layout that works natively with KiCad.

## Get started

**Start at [atopile.io](https://atopile.io)** and choose **Launch atopile** to sign in to the [browser workspace](https://app.atopile.io). Write your circuit in `.ato`, build and validate it, and work on the PCB layout with KiCad in the same workspace. No local editor, extension, or KiCad installation is required.

Follow the quickstart inside the editor, where you'll also find language basics, the standard library reference, and examples. The [documentation landing page](https://docs.atopile.io/) points to the workspace. For existing projects, see the [0.16 transition notes](https://atopile.io/blog/atopile-v16).

## Why atopile

- Reusable modules instead of starting from scratch every time
- Capture intent with equations directly in your design
- Automatic parametric picking of discrete components

## How it works

- `ato` is a declarative language for electronics: modules, interfaces, units, tolerances, and assertions
- The compiler solves constraints, picks parts, runs checks, and updates your KiCad layout
- The browser workspace brings the editor, builds, documentation, and layout tools together

### Where atopile fits in

High-level steps:

- Requirements — capture specs with units, tolerances, and assertions
- Component selection — parametric picking, reuse proven modules
- Design capture — `.ato` modules and interfaces compose your system
- Layout — place and route in KiCad
- Checks — run design checks locally or in CI
- Build outputs — BOM, fabrication and assembly data, reports
- PCB fab/assembly — send outputs to your manufacturer

## Example Projects

Browse the [repository examples](examples) and these hardware projects built with atopile:

- NONOS — Open-source smart speaker https://github.com/atopile/nonos
- DSP - Open-source multi-channel DSP https://github.com/atopile/dsp
- AI-Pin — Vibe-coded Humane Pin https://github.com/atopile/ai-pin
- Hyperion — 300K nit display for raves https://github.com/atopile/hyperion
- ESPaper - ESP32 epaper display driver https://github.com/atopile/hivehaus/tree/master/src/products/espaper

## Contributing and development

This repository contains the open-source compiler and toolchain. The instructions below are for working on atopile itself; start at [atopile.io](https://atopile.io) to design a board.

- Read the [repository overview](AGENTS.md) and [development workflow](.claude/skills/dev/SKILL.md).
- Source setup: [Python and build requirements](pyproject.toml), and the [dependency installation and build steps used in CI](.github/workflows/pytest.yml).
- With a development environment activated, compile native bindings and run tests:

```sh
ato dev compile
ato dev test --llm
```

- From an existing development checkout, create a worktree with a copy of its `.venv` and Zig build artifacts:

```sh
ato dev worktree <suffix> --branch fix/<suffix> --no-cd
cd ../atopile_<suffix>
source .venv/bin/activate
ato --help
```

Omit `--no-cd` to enter an interactive shell in the new worktree automatically.

- Issues and feature requests: https://github.com/atopile/atopile/issues

## Support

- Discord “help” channel: https://discord.gg/CRe5xaDBr3
- Commercial support: hi@atopile.io

## License

MIT. See [LICENSE](LICENSE).
