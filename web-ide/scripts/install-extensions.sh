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

echo ""
echo "=== Installed extensions ==="
${OVSCODE} --list-extensions --extensions-dir "${EXT_DIR}"

echo ""
echo "=== Extension installation complete ==="
