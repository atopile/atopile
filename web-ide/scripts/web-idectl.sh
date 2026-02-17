#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

usage() {
  cat <<'EOF'
Usage: ./scripts/web-idectl.sh <start|status|stop>

Commands:
  start   Build/recreate and start the web-ide stack in background
  status  Show container status and target URLs from .env
  stop    Stop and remove the web-ide stack
EOF
}

if ! command -v podman >/dev/null 2>&1; then
  echo "podman is required but not found in PATH." >&2
  exit 1
fi

command_name="${1:-}"

case "${command_name}" in
  start)
    podman compose up -d --build --force-recreate
    ;;
  status)
    podman compose ps

    bind_addr="${WEB_IDE_BIND_ADDR:-}"
    https_port="${WEB_IDE_HTTPS_PORT:-}"
    public_host="${WEB_IDE_PUBLIC_HOST:-}"

    if [[ -f ".env" ]]; then
      # Load .env values for URL display only.
      set -a
      source ".env"
      set +a
      bind_addr="${WEB_IDE_BIND_ADDR:-$bind_addr}"
      https_port="${WEB_IDE_HTTPS_PORT:-$https_port}"
      public_host="${WEB_IDE_PUBLIC_HOST:-$public_host}"
    fi

    bind_addr="${bind_addr:-0.0.0.0}"
    https_port="${https_port:-3443}"
    public_host="${public_host:-localhost}"

    echo
    echo "URLs:"
    echo "  https://${public_host}:${https_port}"
    echo "  bind: ${bind_addr}:${https_port}"
    ;;
  stop)
    podman compose down
    ;;
  *)
    usage
    exit 2
    ;;
esac
