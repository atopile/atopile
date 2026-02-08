#!/bin/bash
set -e

WORKSPACE="${HOME}/workspace"
DEFAULT_WORKSPACE="/tmp/default-workspace"

# If workspace is empty (e.g. fresh volume mount), seed it with the example project
if [ -d "${DEFAULT_WORKSPACE}" ] && [ -z "$(ls -A "${WORKSPACE}" 2>/dev/null)" ]; then
    echo "[web-ide] Initializing workspace with example project..."
    cp -r "${DEFAULT_WORKSPACE}/." "${WORKSPACE}/"
fi

# Ensure uv symlink exists at the extension-managed globalStorage path.
# The User data dir may be volume-mounted, so recreate this on every startup.
# Runtime data dir is $HOME/.openvscode-server/data/, NOT $OPENVSCODE_SERVER_ROOT/data/
UV_SYMLINK_DIR="${HOME}/.openvscode-server/data/User/globalStorage/atopile.atopile/uv-bin"
mkdir -p "${UV_SYMLINK_DIR}"
ln -sf /usr/local/bin/uv "${UV_SYMLINK_DIR}/uv"

echo "[web-ide] atopile $(ato --version 2>/dev/null || echo 'not found')"
echo "[web-ide] Starting OpenVSCode Server..."

# Exec into OpenVSCode Server (replaces this shell process)
exec "${OPENVSCODE_SERVER_ROOT}/bin/openvscode-server" "$@"
