# atopile

This extension provides syntax highlighting, auto-completion and goto definition for atopile

![demo](/src/vscode-atopile/demo.gif)

## Installation

Install it from your favourite extension store!


## Configuration

### 1. - Easy

If `ato` is in your PATH, the extension will find it automatically.


### 2. - Harder

If not, you can set the `atopile.interpreter` setting in your vscode settings to the path of the `ato` executable.
eg. in your `settings.json` ():
```json
{
    "atopile.interpreter": ["/path/to/the/python/interpreter/used/for/ato"]
}
```

You can find `/path/to/the/python/interpreter/used/for/ato` by running `ato --python-path` in your terminal, where `ato` is available.

These instructions are also in the docs: https://atopile.io/#vscode-extension-extension-store
