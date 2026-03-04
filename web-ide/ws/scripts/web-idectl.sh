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
    # Match VSIX publishing versioning:
    #   Compute versions from local source via `ato --version` / `ato --semver`
    #   and pass them as Docker build args.
    if [[ -z "${ATOPILE_VERSION:-}" || -z "${ATOPILE_SEMVER:-}" ]]; then
      if command -v uv >/dev/null 2>&1; then
        if [[ -z "${ATOPILE_VERSION:-}" ]]; then
          if version="$(uv run ato --version 2>/dev/null)"; then
            export ATOPILE_VERSION="${version}"
          else
            export ATOPILE_VERSION="0.0.0dev"
          fi
        fi
        if [[ -z "${ATOPILE_SEMVER:-}" ]]; then
          if semver="$(uv run ato --semver 2>/dev/null)"; then
            export ATOPILE_SEMVER="${semver}"
          else
            export ATOPILE_SEMVER="0.0.0-dev0"
          fi
        fi
      else
        export ATOPILE_VERSION="${ATOPILE_VERSION:-0.0.0dev}"
        export ATOPILE_SEMVER="${ATOPILE_SEMVER:-0.0.0-dev0}"
      fi
    fi

    echo "Using atopile version: ${ATOPILE_VERSION}"
    echo "Using VSIX semver:     ${ATOPILE_SEMVER}"
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
