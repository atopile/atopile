#!/bin/bash
#
# Development server startup script for atopile UI server.
#
# Architecture (Python owns all state):
#   Browser <--WS--> Python Backend
#
# Starts all required servers in order:
#   1. Python backend (started via CLI; port from DASHBOARD_PORT) - owns ALL state
#   2. Vite dev server (http://localhost:5173) - serves React UI
#
# Usage:
#   ./dev.sh [workspace_path]
#
# Examples:
#   ./dev.sh                                    # Use default workspace
#   ./dev.sh /path/to/workspace                 # Specify workspace
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ports used by our services
DASHBOARD_PORT="${DASHBOARD_PORT:-}"
VITE_PORT=5173

# PIDs of processes we start (for cleanup)
DASHBOARD_PID=""
VITE_PID=""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATOPILE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Default workspace path if none provided
if [ $# -eq 0 ]; then
    WORKSPACE_PATH="$ATOPILE_ROOT"
else
    WORKSPACE_PATH="$1"
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  atopile Webview Development Environment${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Function to kill process on a port
kill_port() {
    local port=$1
    local pids=$(lsof -ti :$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}Killing existing process(es) on port $port: $pids${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 0.5
    fi
}

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down servers...${NC}"
    
    # Kill our started processes
    [ -n "$VITE_PID" ] && kill $VITE_PID 2>/dev/null && echo "  Stopped Vite (PID $VITE_PID)"
    [ -n "$DASHBOARD_PID" ] && kill $DASHBOARD_PID 2>/dev/null && echo "  Stopped Dashboard (PID $DASHBOARD_PID)"
    
    # Also kill anything still on the ports (in case of orphans)
    kill_port $VITE_PORT 2>/dev/null || true
    kill_port $DASHBOARD_PORT 2>/dev/null || true
    
    echo -e "${GREEN}Done.${NC}"
    exit 0
}

# Set up cleanup trap
trap cleanup SIGINT SIGTERM EXIT

# Function to wait for a port to be available
wait_for_port() {
    local port=$1
    local name=$2
    local max_wait=30
    local waited=0
    
    while ! nc -z localhost $port 2>/dev/null; do
        if [ $waited -ge $max_wait ]; then
            echo -e "${RED}Timeout waiting for $name on port $port${NC}"
            return 1
        fi
        sleep 0.5
        waited=$((waited + 1))
    done
    return 0
}

# Step 1: Validate ports and clean up any existing processes
if [ -z "$DASHBOARD_PORT" ]; then
    echo -e "${RED}DASHBOARD_PORT is not set. Start the backend with 'ato serve backend' and export DASHBOARD_PORT.${NC}"
    exit 1
fi
echo -e "${YELLOW}[1/4] Cleaning up existing processes...${NC}"
kill_port $DASHBOARD_PORT
kill_port $VITE_PORT
echo -e "${GREEN}  Done${NC}"
echo ""

# Step 2: Start Python dashboard backend
echo -e "${YELLOW}[2/3] Starting Python backend...${NC}"
echo -e "  Workspace path: $WORKSPACE_PATH"

# Create a temporary Python script to start the dashboard
DASHBOARD_SCRIPT=$(mktemp)
cat > "$DASHBOARD_SCRIPT" << 'PYTHON_EOF'
import sys
import os
from pathlib import Path

# Add atopile to path
sys.path.insert(0, os.environ.get('ATOPILE_ROOT', '.') + '/src')

from atopile.server.server import create_app, find_free_port
import uvicorn

workspace_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
port = int(os.environ['DASHBOARD_PORT'])

# Create a dummy summary file path (builds will create the real one)
summary_file = Path('/tmp/ato-build-summary.json')
summary_file.touch(exist_ok=True)
summary_file.write_text('{"builds": [], "totals": {}}')

app = create_app(
    summary_file=summary_file,
    workspace_path=workspace_path,
)

print(f"Dashboard API starting on http://localhost:{port}")
print(f"  /api/projects - List all projects")
print(f"  /api/summary  - Build summary")
print(f"  /api/build    - Trigger builds")
uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
PYTHON_EOF

# Start the dashboard
ATOPILE_ROOT="$ATOPILE_ROOT" DASHBOARD_PORT=$DASHBOARD_PORT \
    python "$DASHBOARD_SCRIPT" "$WORKSPACE_PATH" &
DASHBOARD_PID=$!

# Wait for dashboard to be ready
if wait_for_port $DASHBOARD_PORT "Dashboard"; then
    echo -e "${GREEN}  Dashboard ready at http://localhost:$DASHBOARD_PORT${NC}"
else
    echo -e "${RED}  Failed to start dashboard${NC}"
    exit 1
fi
echo ""

# Step 3: Start Vite dev server
echo -e "${YELLOW}[3/3] Starting Vite dev server...${NC}"
npm run dev -- --port $VITE_PORT &
VITE_PID=$!

if wait_for_port $VITE_PORT "Vite"; then
    echo -e "${GREEN}  Vite ready at http://localhost:$VITE_PORT${NC}"
else
    echo -e "${RED}  Failed to start Vite${NC}"
    exit 1
fi
echo ""

# All servers started
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}All servers started successfully!${NC}"
echo ""
echo -e "  ${BLUE}UI:${NC}           http://localhost:$VITE_PORT"
echo -e "  ${BLUE}Python API:${NC}   http://localhost:$DASHBOARD_PORT"
echo -e "  ${BLUE}Python WS:${NC}    ws://localhost:$DASHBOARD_PORT/ws/state"
echo ""
echo -e "  ${YELLOW}Architecture:${NC} Browser <-> Python (owns state)"
echo ""
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop all servers"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Wait for any process to exit
wait
