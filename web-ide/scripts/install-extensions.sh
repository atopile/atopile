#!/bin/bash
set -euo pipefail

# Install VS Code extensions in OpenVSCode Server container
# Called during Docker build

OPENVSCODE_SERVER_ROOT="${OPENVSCODE_SERVER_ROOT:-/home/.openvscode-server}"
OVSCODE="${OPENVSCODE_SERVER_ROOT}/bin/openvscode-server"
ARTIFACTS_DIR="/tmp/artifacts"

echo "=== Installing VS Code extensions ==="

# Install atopile extension from local VSIX
echo "Installing atopile extension from VSIX..."
VSIX_FILE=$(find "${ARTIFACTS_DIR}" -name "*.vsix" | head -1)
if [[ -n "${VSIX_FILE}" ]]; then
    ${OVSCODE} --install-extension "${VSIX_FILE}" --force
    echo "Installed: ${VSIX_FILE}"
else
    echo "ERROR: No VSIX file found in ${ARTIFACTS_DIR}"
    exit 1
fi

# Install Python extension from Open VSX
# Note: ms-python.python is available on Open VSX
echo "Installing Python extension from Open VSX..."
${OVSCODE} --install-extension ms-python.python --force || {
    echo "Warning: Failed to install Python extension, continuing..."
}

echo ""
echo "=== Installed extensions ==="
${OVSCODE} --list-extensions

echo ""
echo "=== Extension installation complete ==="
