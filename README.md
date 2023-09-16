# atopile

Compiler for hardware - starting with PCBs


## Usage

There's not a lot here, because it's over at http://docs.atopile.io/


## Development

### Prerequisites / Installation

You'll need >= `python3.10` and `pip` (Use `brew`).

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


## CLI development

ANTLR (or more specifically Java) was a PITA to get working on my Mac... so, I didn't 🤷‍♂️, I just wrapped up ANTLR in a neat little dockerised bundle and make a script that calls out to it easily.

As of writing, that lives in [mawildoer/antlr4](https://github.com/mawildoer/antlr4/tree/mawildoer/simplified-portable-docker/docker-simplified), but [hopefully we can get it into ANTLR mainline](https://github.com/antlr/antlr4/pull/4244) soon.

For now, clone the branch in the first link (eg. to your "repos" or "projects" directory), and then follow the [instructions](https://github.com/mawildoer/antlr4/tree/mawildoer/simplified-portable-docker/docker-simplified) on how to build it.

You can build the grammer to python source with the following command (modified with the appropriate paths for you).

`cd src/atopile/parser`

`/Users/mattwildoer/Projects/antlr4/docker-simplified/antlr4 -Dlanguage=Python3 -visitor AtopileParser.g4 AtopileLexer.g4`


## Front end development

To check out front-end changes live, run `npm run serve` in one terminal and make sure to run `ato view` on a project in another (to provide API access).

This will start the front-end server at `localhost:1234` and the backend at `localhost:2860`. The front-end's development server (`pracel`) will proxy API requests to the backend.


## Syntax highlighting is pretty nice...

You can download the extension from CI here:

![download-artifacts](docs/images/download-artifacts.png)

Then, from your PC `code --install-extension path/to/atopile-*.vsix`
