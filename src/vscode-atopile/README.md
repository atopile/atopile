# atopile VSCode Extension

[![Visual Studio Marketplace Version](https://img.shields.io/visual-studio-marketplace/v/atopile.atopile)](https://marketplace.visualstudio.com/items?itemName=atopile.atopile)
[![Installs](https://img.shields.io/visual-studio-marketplace/i/atopile.atopile)](https://marketplace.visualstudio.com/items?itemName=atopile.atopile)
[![Rating](https://img.shields.io/visual-studio-marketplace/r/atopile.atopile)](https://marketplace.visualstudio.com/items?itemName=atopile.atopile)

The official Visual Studio Code extension for **atopile** - the language and toolchain to design electronics with code.

Design circuit boards with the same powerful workflows that software developers use: version control, modularity, and automated validation. Write human-readable `.ato` files instead of point-and-click schematics.

## ✨ Features

### 🔤 Language Support

- **Syntax highlighting** for `.ato` files with rich semantic coloring
- **IntelliSense** with auto-completion for modules, interfaces, and parameters
- **Go to definition** and **find references** for symbols
- **Hover information** showing parameter types and documentation
- **Error diagnostics** with real-time validation

### 🏗️ Project Management

- **Create new projects** with templates and scaffolding
- **Build integration** with one-click builds and error reporting
- **Build target selection** for different project outputs
- **Project explorer** showing module hierarchy and dependencies

### 📦 Package Management

- **Add packages** from the [atopile package registry](https://packages.atopile.io)
- **Remove packages** with dependency cleanup
- **Package explorer** for browsing available modules
- **Automatic dependency resolution**

### 🔧 Design Tools Integration

- **KiCAD integration** - launch PCB editor directly from VS Code
- **Layout preview** with integrated kicanvas viewer
- **3D model preview** for visualizing your designs
- **Real-time build feedback** with instant error detection

### 🤖 AI & Automation

- **LLM setup** for AI-assisted design with MCP (Model Context Protocol)
- **Code snippets** for common circuit patterns
- **Design validation** with automated checks

## 🚀 Getting Started

### Prerequisites

- Visual Studio Code 1.78.0 or later
- Python extension for VS Code
- Git (recommended for version control)

### Installation

1. **From VS Code Marketplace:**

    - Open VS Code
    - Go to Extensions (Ctrl+Shift+X)
    - Search for "atopile"
    - Click Install

2. **From Command Line:**
    ```bash
    code --install-extension atopile.atopile
    ```

### Quick Start

1. **Create a new project:**

    - Open Command Palette (Ctrl+Shift+P)
    - Run "atopile: Create project"
    - Choose a template and location

2. **Open an example:**

    - Open Command Palette (Ctrl+Shift+P)
    - Run "atopile: Open Example Project"
    - Explore the examples to learn atopile syntax

3. **Start coding:**

    ```ato
    module MyFirstCircuit:
        # Create a simple LED circuit
        led = new LED
        resistor = new Resistor

        # Set component values
        resistor.resistance = 220ohm +/- 5%
        resistor.max_power = 0.25W

        # Connect components
        power.hv ~> resistor ~> led.anode
        led.cathode ~ power.lv
    ```

## 📋 Commands

Access these commands via the Command Palette (Ctrl+Shift+P):

| Command                              | Description                     |
| ------------------------------------ | ------------------------------- |
| `atopile: Create project`            | Create a new atopile project    |
| `atopile: Build`                     | Build the current project       |
| `atopile: Choose build target`       | Select build configuration      |
| `atopile: Add package dependency`    | Install a package from registry |
| `atopile: Remove package dependency` | Remove a package                |
| `atopile: Add part`                  | Add electronic components       |
| `atopile: Launch KiCAD`              | Open PCB in KiCAD editor        |
| `atopile: Open Layout Preview`       | View PCB layout                 |
| `atopile: Open 3D Model Preview`     | View 3D rendering               |
| `atopile: Generate Manufacturing Data` | Generate manufacturing data   |
| `atopile: Package Explorer`          | Browse available packages       |
| `atopile: Restart Server`            | Restart language server         |
| `atopile: Setup LLM rules & MCP`     | Configure AI assistance         |


## 🎯 Workspace Features

The extension provides a dedicated atopile activity bar with:

- **Project Explorer**: Navigate your module hierarchy
- **Quick Actions**: Create projects, add packages, build
- **Examples**: Access sample projects and tutorials

## 🔧 Requirements

- **VS Code**: Version 1.78.0 or later
- **Python Extension**: Required for language server
- **Git Extension**: Recommended for version control

## 🐛 Troubleshooting

### Language Server Issues

If you encounter problems with syntax highlighting or IntelliSense:

1. Run "atopile: Restart Server" from Command Palette
2. Check Output panel → atopile for error messages
3. Verify atopile installation: `ato --version`

### Build Errors

- Ensure your project has a valid `ato.yaml` file
- Check that all dependencies are installed
- Review build output in the integrated terminal

### Missing Features

- Verify the extension is activated (check status bar)
- Try reloading the window (Ctrl+Shift+P → "Developer: Reload Window")

## 📚 Resources

- **Documentation**: [docs.atopile.io](https://docs.atopile.io)
- **Package Registry**: [packages.atopile.io](https://packages.atopile.io)
- **GitHub Repository**: [github.com/atopile/atopile](https://github.com/atopile/atopile)
- **Community**: Join our [Discord]((https://discord.gg/CRe5xaDBr3]https://discord.gg/CRe5xaDBr3)) or [discussions](https://github.com/atopile/atopile/discussions)

## 🤝 Contributing

Found a bug or want to contribute?

- **Issues**: [Report bugs](https://github.com/atopile/atopile/issues)
- **Code**: [Submit PRs](https://github.com/atopile/atopile/pulls)
- **Docs**: Help improve documentation

## 📄 License

This extension is licensed under the [MIT License](https://github.com/atopile/atopile/blob/main/LICENSE).

---

**Happy designing!** 🚀⚡

_Design electronics like software - version controlled, modular, and validated._
