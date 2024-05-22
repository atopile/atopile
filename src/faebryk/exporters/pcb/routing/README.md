# Auto-routing

This folder contains libraries to implement auto-routing for PCBs.
Careful: Not auto-placing.

## Setup

You will need to install [graph-tool](https://graph-tool.skewed.de/) to use auto-routing.

### Arch
```bash
# Install
yay -S python-graph-tool
# Instruct poetry to use system site packages
poetry config virtualenvs.options.system-site-packages true

# Rest of faebryk-app setup
poetry shell
poetry install
```
