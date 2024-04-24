# Development Guide

## Prerequisites

- [Install atopile via git](https://atopile.io/getting-started/#atopile-compiler-with-git)

## Dev Tools

We recommend VSCode for development. If nothing else, it has heaps of high quality extensions and atopile language support, plus it's what we all use internally - so we know how to configure it for purpose.

You should have at minimum:
- [VSCode](https://code.visualstudio.com)
- [VSCode atopile extension](https://marketplace.visualstudio.com/items?itemName=atopile.atopile)
- [Python Extension for VSCode](https://marketplace.visualstudio.com/items?itemName=ms-python.python)

### Verbosity

You can increase the verbosity of atopile by using the `-v` of `-vv` flags, eg. `ato -vv build`

!!! tip "Flag Location"
    Flags are placed after the `ato` command and before the command you want to run. For example, `ato -vv build` will run the build command with the verbose flag set to the highest level, while `ato build -vv` will not work.

### Debugging

You can start the CLI in debug mode by using the `--debug` flag, eg. `ato --debug build`

This will run a [`debugpy`](https://github.com/microsoft/debugpy) server on port `5678` which you can connect to with the VSCode built-in debugger.

![connect debugger](assets/images/debugger-vscode.png)

??? help "Syntax highlighting isn't working"
    If you're having trouble with syntax highlighting in the debugger, it might be because VSCode sets up a mapping between the remote and local file paths by default - remove it.

## Viewer development

### Building the viewer

You first need to build the viewer when installing atopile from it's repository directly. First, navigate to the viewer directly:

``` sh
cd src/atopile/viewer
```

Then install the node dependencies:

``` sh
npm install
```

Finally, build the viewer:

``` sh
npm run build
```

This will create a `dist` directory within the viewer directory. Invoking the `ato view` command will point the server to it.

### Dev viewer server

When working on the viewer, it is quite handy to use the following command to start a dev server:

``` sh
npm run dev
```

As you save your work, vite will automatically rebuild your project and advertise it on a local address. Navigate to the address to inspect your work. We recommend running the `ato view` command from one of your existing projects, so you have a project to look at during development.
