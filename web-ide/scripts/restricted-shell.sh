#!/bin/bash

# Allow non-interactive command execution (used by VS Code for shell env
# resolution, e.g. `bash -c '...'` or `bash -lc '...'`).
# Keep interactive terminal access blocked.
#
# Allowed patterns:
#   --command         GNU long form
#   -c                exactly "-c"
#   -<letters>c       compound short flags ending in c (e.g. -lc, -ic)
for arg in "$@"; do
    case "$arg" in
        --command|-c) exec /bin/bash "$@" ;;
        -[a-zA-Z]*c)  exec /bin/bash "$@" ;;
    esac
done

echo "Terminal access is disabled in the web IDE."
echo "Use the atopile sidebar to build and manage your project."
exit 0
