#!/bin/bash
#
# Orchestrator Quickstart Script
# Starts both the backend server and frontend dev server
# Press Ctrl+C to stop both
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
WEB_DIR="$SCRIPT_DIR/web"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# PIDs for cleanup
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"

    if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo -e "${BLUE}Stopping frontend (PID: $FRONTEND_PID)${NC}"
        kill "$FRONTEND_PID" 2>/dev/null || true
        wait "$FRONTEND_PID" 2>/dev/null || true
    fi

    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo -e "${BLUE}Stopping backend (PID: $BACKEND_PID)${NC}"
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi

    echo -e "${GREEN}Shutdown complete${NC}"
    exit 0
}

# Trap signals for cleanup
trap cleanup SIGINT SIGTERM EXIT

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}   Orchestrator Quickstart${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""

# Check if we're in a virtual environment or can find python
PYTHON_CMD=""
if [ -f "$ROOT_DIR/.venv/bin/python" ]; then
    PYTHON_CMD="$ROOT_DIR/.venv/bin/python"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}Error: Python not found${NC}"
    exit 1
fi

echo -e "${BLUE}Using Python: $PYTHON_CMD${NC}"

# Check if npm is available
if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm not found. Please install Node.js${NC}"
    exit 1
fi

# Check if node_modules exists, if not install
if [ ! -d "$WEB_DIR/node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    (cd "$WEB_DIR" && npm install)
fi

# Start backend server
echo ""
echo -e "${BLUE}Starting backend server on http://localhost:8765${NC}"
cd "$ROOT_DIR"
$PYTHON_CMD -m tools.orchestrator.cli.main serve --port 8765 &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Check if backend started successfully
if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo -e "${RED}Error: Backend failed to start${NC}"
    exit 1
fi

echo -e "${GREEN}Backend started (PID: $BACKEND_PID)${NC}"

# Start frontend dev server
echo ""
echo -e "${BLUE}Starting frontend dev server on http://localhost:5173${NC}"
cd "$WEB_DIR"
npm run dev &
FRONTEND_PID=$!

# Wait a moment for frontend to start
sleep 3

# Check if frontend started successfully
if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo -e "${RED}Error: Frontend failed to start${NC}"
    cleanup
    exit 1
fi

echo -e "${GREEN}Frontend started (PID: $FRONTEND_PID)${NC}"

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}   Orchestrator is running!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "  ${BLUE}Dashboard:${NC}  http://localhost:5173"
echo -e "  ${BLUE}API Docs:${NC}   http://localhost:8765/docs"
echo -e "  ${BLUE}Health:${NC}     http://localhost:8765/health"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"
echo ""

# Wait for either process to exit
wait
