#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SPAWNER_APP="atopile-playground"
WORKSPACE_APP="atopile-ws"
WORKSPACE_REGION="iad"

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Deploy the atopile playground to Fly.io.

Options:
  --spawner-only    Only deploy the spawner (skip workspace image build)
  --workspace-only  Only build and push the workspace image (skip spawner)
  --help            Show this help message

By default, deploys both the workspace image and the spawner.

Required:
  FLY_API_TOKEN     Set in environment (first-time only, or when rotating).
  flyctl            Must be installed (PATH, or ~/.fly/bin/).
EOF
  exit 0
}

# ---------------------------------------------------------------------------
# Parse flags
# ---------------------------------------------------------------------------
DEPLOY_SPAWNER=true
DEPLOY_WORKSPACE=true

for arg in "$@"; do
  case "$arg" in
    --spawner-only)  DEPLOY_WORKSPACE=false ;;
    --workspace-only) DEPLOY_SPAWNER=false ;;
    --help|-h)       usage ;;
    *)               echo "Unknown option: $arg"; usage ;;
  esac
done

echo "=== atopile Playground Deployer ==="
echo ""

# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------
# Resolve flyctl — could be "fly", "flyctl", or in ~/.fly/bin/
if command -v fly &>/dev/null; then
  FLY=fly
elif command -v flyctl &>/dev/null; then
  FLY=flyctl
elif [ -x "${HOME}/.fly/bin/flyctl" ]; then
  FLY="${HOME}/.fly/bin/flyctl"
else
  echo "Error: flyctl not found. Install from https://fly.io/docs/flyctl/install/"
  exit 1
fi

if ! $FLY auth whoami &>/dev/null; then
  echo "Error: Not logged in to Fly.io. Run: $FLY auth login"
  exit 1
fi

echo "Logged in as: $($FLY auth whoami)"
echo ""

# Ensure apps exist
for app in "${WORKSPACE_APP}" "${SPAWNER_APP}"; do
  if $FLY apps list --json | grep -q "\"${app}\""; then
    echo "App ${app}: exists"
  else
    echo "Creating app: ${app}"
    $FLY apps create "${app}"
  fi
done
echo ""

# ---------------------------------------------------------------------------
# Workspace image: build via Fly remote builder → registry.fly.io
# ---------------------------------------------------------------------------
if [ "$DEPLOY_WORKSPACE" = true ]; then
  echo "--- Building workspace image (Fly remote builder)"
  echo "    Dockerfile: web-ide/Dockerfile"
  echo "    Build context: repo root"
  echo ""

  # fly deploy builds the image, pushes to registry.fly.io/atopile-ws:latest,
  # and creates/updates an "app" process group machine. We destroy that machine
  # afterwards since workspace machines are managed by the spawner.
  $FLY deploy \
    --app "${WORKSPACE_APP}" \
    --dockerfile "${REPO_ROOT}/web-ide/Dockerfile" \
    --remote-only \
    --strategy immediate \
    --ha=false

  echo ""
  echo "Image pushed to: registry.fly.io/${WORKSPACE_APP}:latest"

  # Destroy the "app" machine that fly deploy created — the spawner manages
  # workspace machines via the Machines API, not via fly deploy.
  echo ""
  echo "--- Cleaning up deploy-created machine"
  APP_MACHINES=$($FLY machines list --app "${WORKSPACE_APP}" --json 2>/dev/null \
    | python3 -c "
import json, sys
machines = json.load(sys.stdin)
for m in machines:
    pg = (m.get('config', {}).get('metadata', {}).get('fly_process_group')
          or m.get('process_group', ''))
    if pg == 'app':
        print(m['id'])
" 2>/dev/null || true)

  if [ -n "$APP_MACHINES" ]; then
    for mid in $APP_MACHINES; do
      echo "  Destroying deploy machine: ${mid}"
      $FLY machines destroy "${mid}" --app "${WORKSPACE_APP}" --force 2>/dev/null || true
    done
  else
    echo "  No deploy machines to clean up"
  fi

  # Destroy existing spawner-created workspace machines so new sessions
  # get the updated image. The spawner's pool will replenish automatically.
  echo ""
  echo "--- Cycling workspace machines to pick up new image"
  ALL_MACHINES=$($FLY machines list --app "${WORKSPACE_APP}" --json 2>/dev/null \
    | python3 -c "
import json, sys
for m in json.load(sys.stdin):
    print(m['id'])
" 2>/dev/null || true)

  if [ -n "$ALL_MACHINES" ]; then
    for mid in $ALL_MACHINES; do
      echo "  Destroying: ${mid}"
      $FLY machines destroy "${mid}" --app "${WORKSPACE_APP}" --force 2>/dev/null || true
    done
    echo "  Done. Spawner will replenish pool within ~30s."
  else
    echo "  No workspace machines running."
  fi
  echo ""
fi

# ---------------------------------------------------------------------------
# Spawner: set secrets and deploy
# ---------------------------------------------------------------------------
if [ "$DEPLOY_SPAWNER" = true ]; then
  # Only touch secrets if FLY_API_TOKEN is not already configured on the spawner.
  # The token is a runtime secret the spawner uses to call the Machines API —
  # it only needs to be set once (or when rotating tokens).
  EXISTING_SECRETS=$($FLY secrets list --app "${SPAWNER_APP}" --json 2>/dev/null || echo "[]")
  HAS_TOKEN=$(echo "$EXISTING_SECRETS" | python3 -c "
import json, sys
secrets = json.load(sys.stdin)
print('yes' if any(s.get('Name') == 'FLY_API_TOKEN' or s.get('name') == 'FLY_API_TOKEN' for s in secrets) else 'no')
" 2>/dev/null || echo "no")

  if [ "$HAS_TOKEN" = "no" ]; then
    echo "--- Configuring spawner secrets (first-time setup)"
    if [ -z "${FLY_API_TOKEN:-}" ]; then
      echo "FLY_API_TOKEN is not set in environment."
      echo "Create a token at: https://fly.io/dashboard/personal/tokens"
      read -rsp "Enter FLY_API_TOKEN: " FLY_API_TOKEN
      echo ""
    fi
    $FLY secrets set \
      --app "${SPAWNER_APP}" \
      FLY_API_TOKEN="${FLY_API_TOKEN}" \
      WORKSPACE_APP="${WORKSPACE_APP}" \
      WORKSPACE_REGION="${WORKSPACE_REGION}"
    echo "  Secrets configured."
    echo ""
  else
    echo "--- Spawner secrets already configured, skipping."
    echo "    (To rotate: $FLY secrets set --app ${SPAWNER_APP} FLY_API_TOKEN=fo1_...)"
    echo ""
  fi

  echo "--- Deploying spawner"
  # fly deploy uses cwd as build context; the spawner Dockerfile expects
  # server.js in the context root, so we cd into the playground dir.
  # Copy the shared Caddyfile so server.js can read it at runtime.
  cp "${SCRIPT_DIR}/../scripts/Caddyfile" "${SCRIPT_DIR}/Caddyfile"
  (cd "${SCRIPT_DIR}" && $FLY deploy --config fly.spawner.toml)
  rm -f "${SCRIPT_DIR}/Caddyfile"
  echo ""
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo "=== Deployment complete ==="
echo ""
echo "Playground URL: https://${SPAWNER_APP}.fly.dev"
echo ""
echo "Monitor:"
echo "  $FLY logs --app ${SPAWNER_APP}"
echo "  $FLY machines list --app ${WORKSPACE_APP}"
echo ""
echo "Validate:"
echo "  cd web-ide"
echo "  node scripts/validate.mjs 'https://${SPAWNER_APP}.fly.dev' --timeout=120000"
