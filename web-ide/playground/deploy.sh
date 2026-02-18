#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SPAWNER_APP="atopile-playground"
WORKSPACE_APP="atopile-ws"
WORKSPACE_IMAGE="ghcr.io/atopile/atopile-web-ide:latest"
WORKSPACE_REGION="iad"

echo "=== atopile Playground Deployer ==="
echo ""

# Check flyctl is installed
if ! command -v fly &>/dev/null; then
  echo "Error: flyctl (fly) not found. Install from https://fly.io/docs/flyctl/install/"
  exit 1
fi

# Ensure logged in
if ! fly auth whoami &>/dev/null; then
  echo "Error: Not logged in to Fly.io. Run: fly auth login"
  exit 1
fi

echo "Logged in as: $(fly auth whoami)"
echo ""

# Create workspace app (if not exists)
echo "--- Creating workspace app: ${WORKSPACE_APP}"
if fly apps list --json | grep -q "\"${WORKSPACE_APP}\""; then
  echo "  Already exists, skipping."
else
  fly apps create "${WORKSPACE_APP}"
  echo "  Created."
fi
echo ""

# Create spawner app (if not exists)
echo "--- Creating spawner app: ${SPAWNER_APP}"
if fly apps list --json | grep -q "\"${SPAWNER_APP}\""; then
  echo "  Already exists, skipping."
else
  fly apps create "${SPAWNER_APP}"
  echo "  Created."
fi
echo ""

# Set secrets on spawner
echo "--- Configuring secrets on ${SPAWNER_APP}"

if [ -z "${FLY_API_TOKEN:-}" ]; then
  echo "FLY_API_TOKEN is not set in environment."
  echo "Create a token at: https://fly.io/dashboard/personal/tokens"
  read -rsp "Enter FLY_API_TOKEN: " FLY_API_TOKEN
  echo ""
fi

fly secrets set \
  --app "${SPAWNER_APP}" \
  FLY_API_TOKEN="${FLY_API_TOKEN}" \
  WORKSPACE_APP="${WORKSPACE_APP}" \
  WORKSPACE_IMAGE="${WORKSPACE_IMAGE}" \
  WORKSPACE_REGION="${WORKSPACE_REGION}"
echo "  Secrets configured."
echo ""

# Deploy spawner
echo "--- Deploying spawner"
fly deploy --config "${SCRIPT_DIR}/fly.spawner.toml"
echo ""

echo "=== Deployment complete ==="
echo ""
echo "Playground URL: https://${SPAWNER_APP}.fly.dev"
echo ""
echo "To monitor:"
echo "  fly logs --app ${SPAWNER_APP}"
echo "  fly machines list --app ${WORKSPACE_APP}"
