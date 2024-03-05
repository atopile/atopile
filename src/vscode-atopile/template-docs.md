# Template for VS Code python tools extensions

This is a template repository to get you started on building a VS Code extension for your favorite python tool. It could be a linter, formatter, or code analysis, or all of those together. This template will give you the basic building blocks you need to build a VS Code extension for it.

## Programming Languages and Frameworks

The extension template has two parts, the extension part and language server part. The extension part is written in TypeScript, and language server part is written in Python over the [_pygls_][pygls] (Python language server) library.

For the most part you will be working on the python part of the code when using this template. You will be integrating your tool with the extension part using the [Language Server Protocol](https://microsoft.github.io/language-server-protocol). [_pygls_][pygls] currently works on the [version 3.16 of LSP](https://microsoft.github.io/language-server-protocol/specifications/specification-3-16/).

The TypeScript part handles working with VS Code and its UI. The extension template comes with few settings pre configured that can be used by your tool. If you need to add new settings to support your tool, you will have to work with a bit of TypeScript. The extension has examples for few settings that you can follow. You can also look at extensions developed by our team for some of the popular tools as reference.

## Requirements

1. VS Code 1.64.0 or greater
1. Python 3.8 or greater
1. node >= 18.17.0
1. npm >= 8.19.0 (`npm` is installed with node, check npm version, use `npm install -g npm@8.3.0` to update)
1. Python extension for VS Code

You should know to create and work with python virtual environments.

## Getting Started

1. Use this [template to create your repo](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template).
1. Check-out your repo locally on your development machine.
1. Create and activate a python virtual environment for this project in a terminal. Be sure to use the minimum version of python for your tool. This template was written to work with python 3.8 or greater.
1. Install `nox` in the activated environment: `python -m pip install nox`.
1. Add your favorite tool to `requirements.in`
1. Run `nox --session setup`.
1. **Optional** Install test dependencies `python -m pip install -r src/test/python_tests/requirements.txt`. You will have to install these to run tests from the Test Explorer.
1. Open `package.json`, look for and update the following things:
    1. Find and replace `atopile` with module name for your tool. This will be used internally to create settings namespace, register commands, etc. Recommendation is to use lower case version of the name, no spaces, `-` are ok. For example, replacing `atopile` with `pylint` will lead to settings looking like `pylint.args`. Another example, replacing `atopile` with `black-formatter` will make settings look like `black-formatter.args`.
    1. Find and replace `atopile` with display name for your tool. This is used as the title for the extension in market place, extensions view, output logs, etc. For example, for the `black` extension this is `Black Formatter`.
1. Install node packages using `npm install`.
1. Go to https://marketplace.visualstudio.com/vscode and create a publisher account if you don't already have one.
    1. Use the published name in `package.json` by replacing `<my-publisher>` with the name you registered in the marketplace.

## Features of this Template

After finishing the getting started part, this template would have added the following. Assume `atopile` was replaced with `mytool`, and `atopile` with`My Tool`:

1. A command `My Tool: Restart Server` (command Id: `mytool.restart`).
1. Following setting:
    - `mytool.args`
    - `mytool.path`
    - `mytool.importStrategy`
    - `mytool.interpreter`
    - `mytool.showNotification`
1. Following triggers for extension activation:
    - On Language `python`.
    - On File with `.py` extension found in the opened workspace.
1. Following commands are registered:
    - `mytool.restart`: Restarts the language server.
1. Output Channel for logging `Output` > `My Tool`

## Adding features from your tool

Open `bundled/tool/lsp_server.py`, here is where you will do most of the changes. Look for `TODO` comments there for more details.

Also look for `TODO` in other locations in the entire template:

- `bundled/tool/lsp_runner.py` : You may need to update this in some special cases.
- `src/test/python_tests/test_server.py` : This is where you will write tests. There are two incomplete examples provided there to get you started.
- All the markdown files in this template have some `TODO` items, be sure to check them out as well. That includes updating the LICENSE file, even if you want to keep it MIT License.

References, to other extension created by our team using the template:

- Protocol reference: <https://microsoft.github.io/language-server-protocol/specifications/specification-3-16/>
- Implementation showing how to handle Linting on file `open`, `save`, and `close`. [Pylint](https://github.com/microsoft/vscode-pylint/tree/main/bundled/tool)
- Implementation showing how to handle Formatting. [Black Formatter](https://github.com/microsoft/vscode-black-formatter/tree/main/bundled/tool)
- Implementation showing how to handle Code Actions. [isort](https://github.com/microsoft/vscode-isort/blob/main/bundled/tool)

## Building and Run the extension

Run the `Debug Extension and Python` configuration form VS Code. That should build and debug the extension in host window.

Note: if you just want to build you can run the build task in VS Code (`ctrl`+`shift`+`B`)

## Debugging

To debug both TypeScript and Python code use `Debug Extension and Python` debug config. This is the recommended way. Also, when stopping, be sure to stop both the Typescript, and Python debug sessions. Otherwise, it may not reconnect to the python session.

To debug only TypeScript code, use `Debug Extension` debug config.

To debug a already running server or in production server, use `Python Attach`, and select the process that is running `lsp_server.py`.

## Logging and Logs

The template creates a logging Output channel that can be found under `Output` > `mytool` panel. You can control the log level running the `Developer: Set Log Level...` command from the Command Palette, and selecting your extension from the list. It should be listed using the display name for your tool. You can also set the global log level, and that will apply to all extensions and the editor.

If you need logs that involve messages between the Language Client and Language Server, you can set `"mytool.server.trace": "verbose"`, to get the messaging logs. These logs are also available `Output` > `mytool` panel.

## Adding new Settings or Commands

You can add new settings by adding details for the settings in `package.json` file. To pass this configuration to your python tool server (i.e, `lsp_server.py`) update the `settings.ts` as need. There are examples of different types of settings in that file that you can base your new settings on.

You can follow how `restart` command is implemented in `package.json` and `extension.ts` for how to add commands. You can also contribute commands from Python via the Language Server Protocol.

## Testing

See `src\test\python_tests\test_server.py` for starting point. See, other referred projects here for testing various aspects of running the tool over LSP.

If you have installed the test requirements you should be able to see the tests in the test explorer.

You can also run all tests using `nox --session tests` command.

## Linting

Run `nox --session lint` to run linting on both Python and TypeScript code. Please update the nox file if you want to use a different linter and formatter.

## Packaging and Publishing

1. Update various fields in `package.json`. At minimum, check the following fields and update them accordingly. See [extension manifest reference](https://code.visualstudio.com/api/references/extension-manifest) to add more fields:
    - `"publisher"`: Update this to your publisher id from <https://marketplace.visualstudio.com/>.
    - `"version"`: See <https://semver.org/> for details of requirements and limitations for this field.
    - `"license"`: Update license as per your project. Defaults to `MIT`.
    - `"keywords"`: Update keywords for your project, these will be used when searching in the VS Code marketplace.
    - `"categories"`: Update categories for your project, makes it easier to filter in the VS Code marketplace.
    - `"homepage"`, `"repository"`, and `"bugs"` : Update URLs for these fields to point to your project.
    - **Optional** Add `"icon"` field with relative path to a image file to use as icon for this project.
1. Make sure to check the following markdown files:
    - **REQUIRED** First time only: `CODE_OF_CONDUCT.md`, `LICENSE`, `SUPPORT.md`, `SECURITY.md`
    - Every Release: `CHANGELOG.md`
1. Build package using `nox --session build_package`.
1. Take the generated `.vsix` file and upload it to your extension management page <https://marketplace.visualstudio.com/manage>.

To do this from the command line see here <https://code.visualstudio.com/api/working-with-extensions/publishing-extension>

## Upgrading Dependencies

Dependabot yml is provided to make it easy to setup upgrading dependencies in this extension. Be sure to add the labels used in the dependabot to your repo.

To manually upgrade your local project:

1. Create a new branch
1. Run `npm update` to update node modules.
1. Run `nox --session setup` to upgrade python packages.

## Troubleshooting

### Changing path or name of `lsp_server.py` something else

If you want to change the name of `lsp_server.py` to something else, you can. Be sure to update `constants.ts` and `src\test\python_tests\lsp_test_client\session.py`.

Also make sure that the inserted paths in `lsp_server.py` are pointing to the right folders to pick up the dependent packages.

### Module not found errors

This can occurs if `bundled/libs` is empty. That is the folder where we put your tool and other dependencies. Be sure to follow the build steps need for creating and bundling the required libs.

Common one is [_pygls_][pygls] module not found.

# TODO: The maintainer of this repo has not yet edited this file

**Repo Owner** Make sure you update this. As a repository owner you will need to update this file with specific instructions for your extension.

[pygls]: https://github.com/openlawlibrary/pygls
