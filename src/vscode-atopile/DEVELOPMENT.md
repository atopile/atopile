# Development

## Recommended Workflow

Use the debugging tools "Debug Extension and Python Attach to Process" to run the extension in a new window. This will allow you to see the output of the extension in the debug console.

## Backup

I've had trouble with the development tools here. Specifically, I'm unconvinced the python LSP debugger is working correctly.

For the sake of basic validation, it's also easy to run the following command to build the package:

`vsce package --pre-release --no-git-tag-version --no-update-package-json 1000.0.0`
