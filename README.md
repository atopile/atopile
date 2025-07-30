<h1 align="center">
    <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://github.com/atopile/atopile/assets/9785003/00f19584-18a2-4b5f-9ce4-1248798974dd">
    <source media="(prefers-color-scheme: light)" src="https://github.com/atopile/atopile/assets/9785003/d38941c1-d7c1-42e6-9b94-a62a0996bc19">
    <img alt="atopile logo" src="https://github.com/atopile/atopile/assets/9785003/d38941c1-d7c1-42e6-9b94-a62a0996bc19">
    </picture>
</h1>

# atopile – Hardware design at the speed of software

**atopile** is an open-source language, compiler and tool-chain for designing electronics with code instead of point-and-click schematics. Write human-readable `.ato` files, version them with Git, and let the compiler generate the PCB artifacts for you.

---

## 🧩 What makes atopile different?

|                               |                                                                                                                                                                                                                                                                                                      |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ⚡ **Move fast, stay safe**   | Treat hardware like software: branch, PR, review & merge. Every build re-compiles the design, solves equations and runs automated checks so you can refactor fearlessly.                                                                                                                             |
| 📦 **Modular reuse**          | Install proven sub-circuits from [packages.atopile.io](https://packages.atopile.io) with a single command. Drop-in modules already include schematic, PCB layout – and with the KiCad plugin – _placement & routing_ reuse.                                                                          |
| 🏪 **Millions of components** | Need a 0402 10 kΩ resistor? A single line `new Resistor  • resistance = 10 kΩ ±5 %` auto-picks a part from a database of >10 million manufacturer parts.                                                                                                                                             |
| 📝 **Design intent in code**  | Express requirements, not footprints. Voltages, tolerances, interface contracts and equations live next to the net-list so your intent is always machine-checked.<br/>_Example:_ specify `fc = 10 kHz ±15 %` for a first-order RC filter and the compiler picks matching R & C values automatically. |
| 🗂 **Versioned hardware**      | A PCB revision is just a Git hash. Tag, bisect and branch your board the same way you manage firmware.                                                                                                                                                                                               |

---

## 🚀 Key capabilities

- **Physical-unit aware equations** – Write `vout = vin * R2/(R1+R2)` and assert `vout within 3.3 V ±3 %`.
- **Automatic part selection** – Passive values & package footprints are selected by the compiler based on your constraints.
- **Layout reuse** – Import a power supply module and its pre-routed layout is placed instantly in KiCad.
- **VS Code extension** – Design, build and visualise directly inside Visual Studio Code.
- **Cross-platform** – macOS, Linux, Windows. Container images available for CI.
- **CI artifacts** – Provided GitHub Actions workflow builds your board on every commit, producing BoM, Gerbers and 3D previews automatically—no more copy-pasting values between tools.

---

## 🔧 Quick start

1. Open **Visual Studio Code**.
2. In the Extensions sidebar search for **“atopile”** and click **Install**.
3. Press `Ctrl + Shift + P` / `⌘ + Shift + P` and run **“atopile: Create project”** to scaffold a new design, or choose **“atopile: Open Example Project”** to explore.

That’s it! The extension bundles the compiler, language server and KiCad integration – no extra installs required.

Read the [full quick-start guide →](https://docs.atopile.io/quickstart)

---

## 🤔 Why capture hardware in code?

1. **Repeatability** – Rebuild the entire design pipeline in CI to guarantee nothing drifts between “works on my machine” and production.
2. **Composability** – A DC/DC module written once can power every future design; just set `vout` and you’re done.
3. **Collaboration** – Code-reviews scale better than PDF schematics; nuanced changes are obvious in a diff.
4. **Automation** – Parametric BoM generation, pin-mapping, rule-checking and documentation all flow from the source.

---

## 🌐 Join the community

- Browse community modules at [packages.atopile.io](https://packages.atopile.io)
- Chat with us on [Discord](https://discord.gg/XyGVy6WjY6)
- Follow new releases on [Twitter /X](https://twitter.com/atopile)

---

Licensed under the MIT License. Happy hacking! 🍰
