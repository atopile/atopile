#!/bin/bash
set -euo pipefail
#
# Build-time setup for the atopile web-IDE container.
# Runs as the non-root openvscode-server user (see Dockerfile USER directive).
#
# Expects these env vars (set in the Dockerfile):
#   OPENVSCODE_SERVER_ROOT  – where OpenVSCode Server is installed
#   HOME                    – openvscode-server user's home dir
#
# Expects these directories to be pre-populated by COPY steps:
#   /tmp/artifacts/  – atopile .whl + .vsix from builder stages
#   /tmp/scripts/    – entrypoint.sh, Caddyfile, settings.json, keybindings.json
#   /tmp/branding/   – apply-branding.sh + assets
#

OVSCODE="${OPENVSCODE_SERVER_ROOT}/bin/openvscode-server"
EXT_DIR="${OPENVSCODE_SERVER_ROOT}/extensions"

# ── 1. Install atopile from wheel ────────────────────────────────
# Python version must match requires-python in pyproject.toml (>=3.14,<3.15)
uv tool install --python 3.14 /tmp/artifacts/atopile-*.whl

# ── 2. Install VS Code extensions ────────────────────────────────
# Extensions go into the server's own extensions dir so they load as built-ins.
# The default --install-extension target ($HOME/.openvscode-server/extensions/)
# is NOT scanned by OpenVSCode Server at runtime.

echo "=== Installing VS Code extensions to ${EXT_DIR} ==="

# atopile extension (from local VSIX built in stage 3)
VSIX_FILE=$(find /tmp/artifacts -name "*.vsix" | head -1)
if [[ -n "${VSIX_FILE}" ]]; then
    ${OVSCODE} --install-extension "${VSIX_FILE}" --force --extensions-dir "${EXT_DIR}"
    echo "Installed: ${VSIX_FILE}"
else
    echo "ERROR: No VSIX file found in /tmp/artifacts"
    exit 1
fi

# Python language support (from Open VSX registry)
${OVSCODE} --install-extension ms-python.python --force --extensions-dir "${EXT_DIR}" || {
    echo "Warning: Failed to install Python extension, continuing..."
}

# ── 3. Remove dangerous built-in extensions (security hardening) ─
# Can't use --uninstall-extension for built-ins; delete dirs directly.
# Built-ins have no version suffix (e.g. "debug-auto-launch"),
# marketplace installs do (e.g. "ms-python.debugpy-2025.18.0-linux-x64").

echo "Removing dangerous extensions..."

# Debug/run — prevent arbitrary code execution via debug launch configs
rm -rf "${EXT_DIR}"/ms-python.debugpy*
rm -rf "${EXT_DIR}"/debug-auto-launch
rm -rf "${EXT_DIR}"/debug-server-ready

# Task runners — can execute arbitrary shell commands via tasks.json
rm -rf "${EXT_DIR}"/npm
rm -rf "${EXT_DIR}"/grunt
rm -rf "${EXT_DIR}"/gulp
rm -rf "${EXT_DIR}"/jake

# Git — prevent clone/push/pull from the command palette
rm -rf "${EXT_DIR}"/git
rm -rf "${EXT_DIR}"/git-base
rm -rf "${EXT_DIR}"/github*

# Copilot / Chat — built-in AI features not applicable in web-ide
rm -rf "${EXT_DIR}"/github.copilot*
rm -rf "${EXT_DIR}"/copilot*
rm -rf "${EXT_DIR}"/mermaid-chat-features
rm -rf "${EXT_DIR}"/prompt-basics

# Misc — tunnel forwarding (network escape), config editing (settings bypass)
rm -rf "${EXT_DIR}"/tunnel-forwarding
rm -rf "${EXT_DIR}"/configuration-editing

echo "=== Remaining extensions ==="
${OVSCODE} --list-extensions --extensions-dir "${EXT_DIR}"

# ── 4. Apply branding ────────────────────────────────────────────
/tmp/branding/apply-branding.sh

# ── 5. Place config files ────────────────────────────────────────
# openvscode-server uses ${HOME}/.openvscode-server/data/ as user-data-dir at runtime.
# ${OPENVSCODE_SERVER_ROOT}/data/ is the server installation dir — settings written
# there are NOT read by VS Code. Confirmed by inspecting the running process.

# Machine settings — editor defaults that the user cannot override via the UI
USER_DATA_DIR="${HOME}/.openvscode-server/data"
mkdir -p "${USER_DATA_DIR}/Machine"
cp /tmp/scripts/settings.json "${USER_DATA_DIR}/Machine/settings.json"

# User settings — workbench.colorTheme is window-scoped, must live here (not Machine)
# User keybindings
mkdir -p "${USER_DATA_DIR}/User"
echo '{"workbench.colorTheme": "Default Dark Modern"}' > "${USER_DATA_DIR}/User/settings.json"
cp /tmp/scripts/keybindings.json "${USER_DATA_DIR}/User/keybindings.json"

# Entrypoint + Caddy config
mkdir -p "${HOME}/.local/etc"
cp /tmp/scripts/entrypoint.sh "${HOME}/.local/bin/entrypoint.sh"
chmod +x "${HOME}/.local/bin/entrypoint.sh"
cp /tmp/scripts/Caddyfile "${HOME}/.local/etc/Caddyfile"

# ── 6. uv symlink ────────────────────────────────────────────────
# The atopile extension expects uv at this globalStorage path
UV_SYMLINK_DIR="${HOME}/.openvscode-server/data/User/globalStorage/atopile.atopile/uv-bin"
mkdir -p "${UV_SYMLINK_DIR}"
ln -sf /usr/local/bin/uv "${UV_SYMLINK_DIR}/uv"

# ── 7. Clean up build artifacts ──────────────────────────────────
rm -rf /tmp/artifacts /tmp/setup /tmp/scripts /tmp/branding
