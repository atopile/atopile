# atopile

This extension provides syntax highlighting, auto-completion and goto definition for atopile

![demo](/src/vscode-atopile/demo.gif)

## Installation

Instructions from the docs: https://atopile.io/getting-started/#vscode-extension-extension-store

There's a small amount of one-time configuration required to get type-hints from the extension.

1. Get the path to your python interpreter that has ato installed. This is usually in a virtual environment.
   - You can find this by running `which python` while your venv is activated.
2. Configure VSCode to use it!
   - `Cmd + Shift + P` (or `Ctrl + Shift + P` on Windows) to open the command palette
   - Type "Python: Select Interpreter" and select it
   - If your venv isn't there, you can add it by selecting "Enter interpreter path" and pasting the path to your venv's python binary.

All together now!

![](/docs/assets/images/extension-python-setup.gif)
