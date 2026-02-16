#!/bin/bash

# Allow non-interactive command execution (used by VS Code for shell env resolution).
# Keep interactive terminal access blocked.
for arg in "$@"; do
    if [[ "$arg" == "--command" ]] || ([[ "$arg" == -* ]] && [[ "$arg" == *c* ]]); then
        exec /bin/bash "$@"
    fi
done

echo "Terminal access is disabled in the web IDE."
echo "Use the atopile sidebar to build and manage your project."
exit 0
