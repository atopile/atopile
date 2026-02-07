#!/bin/bash
set -e

WORKSPACE="${HOME}/workspace"
DEFAULT_WORKSPACE="/tmp/default-workspace"

# If workspace is empty (e.g. fresh volume mount), seed it with the example project
if [ -d "${DEFAULT_WORKSPACE}" ] && [ -z "$(ls -A "${WORKSPACE}" 2>/dev/null)" ]; then
    echo "[web-ide] Initializing workspace with example project..."
    cp -r "${DEFAULT_WORKSPACE}/." "${WORKSPACE}/"
fi

echo "[web-ide] atopile $(ato --version 2>/dev/null || echo 'not found')"
echo "[web-ide] Starting OpenVSCode Server..."

# Exec into OpenVSCode Server (replaces this shell process)
exec "${OPENVSCODE_SERVER_ROOT}/bin/openvscode-server" "$@"
