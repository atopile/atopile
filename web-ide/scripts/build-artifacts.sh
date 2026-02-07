#!/bin/bash
set -euo pipefail

# Build atopile wheel and VS Code extension locally.
#
# NOTE: This script is OPTIONAL. The Dockerfile builds everything from source
# inside Docker (multi-stage build). This script is useful for:
#   - Quick local testing of the wheel or VSIX
#   - Building on the host for non-Docker workflows
#
# The wheel built here is platform-specific (e.g. macOS on Mac, Linux on Linux).
# For Docker, use `docker compose up --build` which builds a Linux wheel inside Docker.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_IDE_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$WEB_IDE_DIR")"
ARTIFACTS_DIR="${WEB_IDE_DIR}/artifacts"

echo "=== Building atopile artifacts ==="
echo "Repo root: ${REPO_ROOT}"
echo "Artifacts dir: ${ARTIFACTS_DIR}"

# Create artifacts directory
mkdir -p "${ARTIFACTS_DIR}"

# Clean old artifacts
rm -f "${ARTIFACTS_DIR}"/*.whl
rm -f "${ARTIFACTS_DIR}"/*.vsix

echo ""
echo "=== Building Python wheel ==="
cd "${REPO_ROOT}"
uv build --wheel --out-dir "${ARTIFACTS_DIR}"

echo ""
echo "=== Building VS Code extension ==="
cd "${REPO_ROOT}/src/vscode-atopile"

# Install dependencies
npm ci

# Build webviews and package extension
npm run vscode:prepublish

# Package as VSIX
npx vsce package --out "${ARTIFACTS_DIR}/"

echo ""
echo "=== Build complete ==="
echo "Artifacts:"
ls -la "${ARTIFACTS_DIR}"
echo ""
echo "NOTE: The wheel is platform-specific to this host."
echo "For Docker builds, use: docker compose up --build (builds from source inside Docker)"
