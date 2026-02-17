#!/bin/bash
set -euo pipefail

# Install VS Code extensions in OpenVSCode Server container
# Called during Docker build

OPENVSCODE_SERVER_ROOT="${OPENVSCODE_SERVER_ROOT:-/home/.openvscode-server}"
OVSCODE="${OPENVSCODE_SERVER_ROOT}/bin/openvscode-server"
ARTIFACTS_DIR="/tmp/artifacts"

# Install extensions into the server's own extensions directory so they load
# as built-in extensions. The default --install-extension puts them under
# $HOME/.openvscode-server/extensions/ which the server doesn't scan at runtime.
EXT_DIR="${OPENVSCODE_SERVER_ROOT}/extensions"

echo "=== Installing VS Code extensions to ${EXT_DIR} ==="

# Install atopile extension from local VSIX
echo "Installing atopile extension from VSIX..."
VSIX_FILE=$(find "${ARTIFACTS_DIR}" -name "*.vsix" | head -1)
if [[ -n "${VSIX_FILE}" ]]; then
    ${OVSCODE} --install-extension "${VSIX_FILE}" --force --extensions-dir "${EXT_DIR}"
    echo "Installed: ${VSIX_FILE}"
else
    echo "ERROR: No VSIX file found in ${ARTIFACTS_DIR}"
    exit 1
fi

# Install Python extension from Open VSX
echo "Installing Python extension from Open VSX..."
${OVSCODE} --install-extension ms-python.python --force --extensions-dir "${EXT_DIR}" || {
    echo "Warning: Failed to install Python extension, continuing..."
}

# Remove debug extensions to disable debug/run functionality in the web IDE.
# Can't use --uninstall-extension for built-ins; must delete directories directly.
# Built-in extensions have no version suffix (e.g. "debug-auto-launch"),
# while installed extensions do (e.g. "ms-python.debugpy-2025.18.0-linux-x64").
echo "Removing debug extensions (security hardening)..."
rm -rf "${EXT_DIR}"/ms-python.debugpy*
rm -rf "${EXT_DIR}"/debug-auto-launch
rm -rf "${EXT_DIR}"/debug-server-ready

# Remove task runner extensions (can execute arbitrary shell commands via tasks.json)
rm -rf "${EXT_DIR}"/npm
rm -rf "${EXT_DIR}"/grunt
rm -rf "${EXT_DIR}"/gulp
rm -rf "${EXT_DIR}"/jake

# Remove git extensions (prevent clone/push/pull from command palette)
rm -rf "${EXT_DIR}"/git
rm -rf "${EXT_DIR}"/git-base
rm -rf "${EXT_DIR}"/github*

# Remove other dangerous extensions
rm -rf "${EXT_DIR}"/tunnel-forwarding
rm -rf "${EXT_DIR}"/configuration-editing

echo ""
echo "=== Installed extensions ==="
${OVSCODE} --list-extensions --extensions-dir "${EXT_DIR}"

echo ""
echo "=== Extension installation complete ==="
