#!/bin/bash
# Debug helper for atopile VS Code extension development
#
# Usage: ./scripts/debug-extension.sh [command]
#
# Commands:
#   status    - Show current status of backend and extension
#   logs      - Tail extension logs from Cursor
#   backend   - Start backend with verbose logging
#   rebuild   - Rebuild and reinstall extension
#   webview   - Instructions for debugging webview

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXT_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$(dirname "$EXT_DIR")")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

status() {
    echo -e "${BLUE}=== Backend Status ===${NC}"

    # Check port file
    PORT_FILE="$REPO_ROOT/.atopile/.server_port"
    if [ -f "$PORT_FILE" ]; then
        PORT=$(cat "$PORT_FILE")
        echo -e "Port file: ${GREEN}$PORT_FILE${NC} (port: $PORT)"
    else
        PORT=8501
        echo -e "Port file: ${YELLOW}not found${NC} (using default: $PORT)"
    fi

    # Check health
    if curl -s "http://localhost:$PORT/health" | grep -q "ok"; then
        echo -e "Health check: ${GREEN}OK${NC} (http://localhost:$PORT)"
    else
        echo -e "Health check: ${RED}FAILED${NC}"
    fi

    # Check processes
    echo -e "\n${BLUE}=== Processes ===${NC}"
    pgrep -fl "atopile.server" || echo "No atopile.server processes"

    echo -e "\n${BLUE}=== Extension Logs Location ===${NC}"
    echo "Open Cursor and run: Developer: Show Logs... > Extension Host"
    echo "Or check: ~/Library/Application Support/Cursor/logs/"

    echo -e "\n${BLUE}=== Webview Debugging ===${NC}"
    echo "In Cursor, run command: Developer: Open Webview Developer Tools"
}

logs() {
    echo -e "${BLUE}=== Extension Host Logs ===${NC}"
    LOG_DIR="$HOME/Library/Application Support/Cursor/logs"

    # Find most recent exthost log
    LATEST_LOG=$(find "$LOG_DIR" -name "exthost*.log" -type f 2>/dev/null | head -1)

    if [ -n "$LATEST_LOG" ]; then
        echo "Tailing: $LATEST_LOG"
        echo "Press Ctrl+C to stop"
        echo "---"
        tail -f "$LATEST_LOG" | grep -i --line-buffered "atopile\|backend\|websocket\|error"
    else
        echo -e "${YELLOW}No extension host logs found${NC}"
        echo "Try: Developer: Show Logs... in Cursor"
    fi
}

backend() {
    echo -e "${BLUE}=== Starting Backend with Verbose Logging ===${NC}"

    # Kill existing
    pkill -f "atopile.server" 2>/dev/null || true
    sleep 1

    # Start with debug output
    cd "$REPO_ROOT"
    python -m atopile.server --workspace "$REPO_ROOT" 2>&1 | tee /tmp/atopile-backend.log
}

rebuild() {
    echo -e "${BLUE}=== Rebuilding Extension ===${NC}"
    cd "$EXT_DIR"

    echo "Building webviews..."
    npm run build:webviews

    echo "Packaging extension..."
    npm run package

    echo "Creating VSIX..."
    npx vsce package --no-dependencies

    VSIX=$(ls -t *.vsix | head -1)
    echo -e "${GREEN}Built: $VSIX${NC}"

    echo "Installing in Cursor..."
    cursor --install-extension "$EXT_DIR/$VSIX" --force

    echo -e "${GREEN}Done! Reload Cursor window to apply changes.${NC}"
    echo "Command: Developer: Reload Window"
}

webview() {
    echo -e "${BLUE}=== Webview Debugging Instructions ===${NC}"
    echo ""
    echo "1. Open Cursor Command Palette (Cmd+Shift+P)"
    echo "2. Run: Developer: Open Webview Developer Tools"
    echo "3. Select the atopile webview"
    echo "4. Check Console tab for JavaScript errors"
    echo "5. Check Network tab for failed requests"
    echo ""
    echo -e "${YELLOW}Common issues:${NC}"
    echo "- Blank page: Check Console for CSP errors or connection failures"
    echo "- WebSocket errors: Backend might not be running or wrong port"
    echo "- 404 errors: Assets not built correctly"
}

# Main
case "${1:-status}" in
    status)
        status
        ;;
    logs)
        logs
        ;;
    backend)
        backend
        ;;
    rebuild)
        rebuild
        ;;
    webview)
        webview
        ;;
    *)
        echo "Usage: $0 {status|logs|backend|rebuild|webview}"
        exit 1
        ;;
esac
