# Installation

Ultimately `atopile` is a python package, so you can install it where and however you want - but some python package managers are better than others. Here's how we recommend you install atopile.


## Homebrew `brew` <small>(recommended for macOS)</small>

<!-- --8<-- [start:brew] -->
``` sh
brew install atopile/tap/atopile
```
<!-- --8<-- [end:brew] -->


## `uv` <small>(recommended for other platforms)</small>
<!-- --8<-- [start:uv] -->
1. Install `uv`. See: https://docs.astral.sh/uv/getting-started/installation/

2. Install atopile with `uv`

    ``` sh
    uv tool install atopile
    ```

    !!! important
        `uv` if this is the first time you've used `uv` for a tool install, it might give you another command to run to finish setup.
        Do it.

3. Check `ato` is installed

    ``` sh
    ato --version
    ```
<!-- --8<-- [end:uv] -->


### Editable installation (Best for development)

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
