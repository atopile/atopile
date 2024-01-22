# atopile

Compiler for hardware - starting with PCBs


## Usage

There's not a lot here, because it's over at http://docs.atopile.io/


## Development

### Prerequisites / Installation

You'll need >= `python3.11` and `pip` (Use `brew`).

I'd strongly recommend developing within a `venv`

Since we'll be using this `venv` for both work within this tool directory and whatever projects you're using it on, I'd recommend creating something along the lines of an `atopile-workspace` or `ato-ws` directory somewhere, and then creating a `venv` in there. This means if you do something like a `git clean -xdf` to remove crud, you won't blow away your `venv` with it.

If you decide to follow this, you'll end up with something like this:

```
atopile-workspace
├── .venv --> your virtual environment
├── atopile --> this repo
├── atopile.code-workspace --> vscode workspace file
└── bike-light --> project using atopile
```

Clone this repo.

Wherever you stick the `venv`, you can create the venv with  `python3.11 -m venv .venv` and then `source .venv/bin/activate`

For cli development (so practically all the time) : `pip install -e ."[dev,test,docs]"`

You'll need `npm` for front-end development (`brew install node`).

For any front-end development, you'll also need to install the front-end dependencies: `npm install`


## Syntax highlighting is pretty nice...

You can download the extension from CI here:

![download-artifacts](docs/images/download-artifacts.png)

Then, from your PC `code --install-extension path/to/atopile-*.vsix`
