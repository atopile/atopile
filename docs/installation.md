# Installation

!!! warning
    Check out the [quickstart guide](quickstart.md) for a step-by-step guide for the recommended way to install atopile.
    This page provides alternative installation methods.

Ultimately `atopile` is a python package, so you can install it where and however you want - but some python package managers are better than others. Here's how we recommend you install atopile.

## Editable installation (Best for development)

1. Install `uv`
    See: https://docs.astral.sh/uv/getting-started/installation/

3. Clone the repo

    ``` sh
    git clone https://github.com/atopile/atopile
    ```

4. `cd` into the repo

    ``` sh
    cd atopile
    ```

5. Install

    ``` sh
    uv sync --dev
    ```

## Via `brew`

We would recommend this, however it's not yet quite ready

``` sh
brew install atopile/tap/atopile
```
