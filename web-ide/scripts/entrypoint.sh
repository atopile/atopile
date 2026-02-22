#!/bin/bash
set -e

WORKSPACE="${HOME}/workspace"
DEFAULT_WORKSPACE="/tmp/default-workspace"

# If workspace is empty (e.g. fresh volume mount), seed it with the example project
if [ -d "${DEFAULT_WORKSPACE}" ] && [ -z "$(ls -A "${WORKSPACE}" 2>/dev/null)" ]; then
    echo "[web-ide] Initializing workspace with example project..."
    cp -r "${DEFAULT_WORKSPACE}/." "${WORKSPACE}/"
fi

# Restrict browsing of sensitive directories (e.g. VS Code file picker)
mkdir -p "${HOME}/.openvscode-server" "${HOME}/.local" "${HOME}/.config"
chmod 700 "${HOME}/.openvscode-server" "${HOME}/.local" "${HOME}/.config"

# Ensure uv symlink exists at the extension-managed globalStorage path.
# The User data dir may be volume-mounted, so recreate this on every startup.
# Runtime data dir is $HOME/.openvscode-server/data/, NOT $OPENVSCODE_SERVER_ROOT/data/
UV_SYMLINK_DIR="${HOME}/.openvscode-server/data/User/globalStorage/atopile.atopile/uv-bin"
mkdir -p "${UV_SYMLINK_DIR}"
ln -sf /usr/local/bin/uv "${UV_SYMLINK_DIR}/uv"

# Restore keybindings on every startup (volume mount shadows the build-time copy)
KEYBINDINGS_SRC="${HOME}/.local/etc/keybindings.json"
KEYBINDINGS_DST="${HOME}/.openvscode-server/data/User/keybindings.json"
if [ -f "${KEYBINDINGS_SRC}" ]; then
    mkdir -p "$(dirname "${KEYBINDINGS_DST}")"
    cp "${KEYBINDINGS_SRC}" "${KEYBINDINGS_DST}"
fi

# Pre-start backend server (extension will detect and reuse it)
echo "[web-ide] Pre-starting backend server on port ${ATOPILE_BACKEND_PORT}..."
ato serve backend \
    --port "${ATOPILE_BACKEND_PORT}" \
    --host "${ATOPILE_BACKEND_HOST}" \
    --no-gen \
    --workspace "${WORKSPACE}" &
BACKEND_PID=$!

echo "[web-ide] atopile $(ato --version 2>/dev/null || echo 'not found')"
echo "[web-ide] Starting Caddy reverse proxy and OpenVSCode Server..."

# --- Dual-process management: Caddy + OpenVSCode Server ---
# Both run in background; we forward signals and exit when either dies.

cleanup() {
    echo "[web-ide] Shutting down..."
    kill "$CADDY_PID" "$OPENVSCODE_PID" "$BACKEND_PID" 2>/dev/null
    wait "$CADDY_PID" "$OPENVSCODE_PID" "$BACKEND_PID" 2>/dev/null
}
trap cleanup SIGTERM SIGINT

# Start Caddy (reverse proxy on :3443 → OpenVSCode :3001 + backend :8501)
caddy run --config "${HOME}/.local/etc/Caddyfile" &
CADDY_PID=$!

# Start OpenVSCode Server (listens on 127.0.0.1:3001, behind Caddy)
"${OPENVSCODE_SERVER_ROOT}/bin/openvscode-server" "$@" &
OPENVSCODE_PID=$!

# Wait for either process to exit, then tear down the other
wait -n "$CADDY_PID" "$OPENVSCODE_PID" 2>/dev/null
EXIT_CODE=$?
cleanup
exit $EXIT_CODE
