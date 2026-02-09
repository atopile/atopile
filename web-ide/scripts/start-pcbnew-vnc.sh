#!/bin/bash
set -euo pipefail

# Start a VNC-accessible PCBnew session inside the Docker container.
# Usage: start-pcbnew-vnc.sh [path/to/file.kicad_pcb]
#
# Components launched:
#   Xvfb        – virtual framebuffer X server on :99
#   openbox     – lightweight window manager (PCBnew needs one for dialogs/menus)
#   x11vnc      – VNC server watching :99
#   websockify  – WebSocket-to-TCP proxy (ws://6080 → tcp://5900)
#   pcbnew      – KiCad PCB editor

PCB_FILE="${1:-}"
DISPLAY_NUM=99
VNC_PORT=5900
WS_PORT=6080
RESOLUTION="${RESOLUTION:-1920x1080x24}"

export DISPLAY=:${DISPLAY_NUM}

# Cleanup function
cleanup() {
    kill "$PCBNEW_PID" "$WEBSOCKIFY_PID" "$X11VNC_PID" "$OPENBOX_PID" "$XVFB_PID" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Start Xvfb (virtual display)
Xvfb ":${DISPLAY_NUM}" -screen 0 "${RESOLUTION}" &
XVFB_PID=$!
sleep 1

# Start openbox window manager
openbox &
OPENBOX_PID=$!

# Start x11vnc — localhost only, no password, shared access
x11vnc -display ":${DISPLAY_NUM}" -nopw -listen localhost -forever -shared -rfbport "${VNC_PORT}" \
  -threads \
  -noxdamage \
  -allinput \
  -defer 0 \
  -wait 5 \
  -nonap &
X11VNC_PID=$!
sleep 1

# Start websockify — bridges WebSocket to VNC
websockify --web /usr/share/novnc "${WS_PORT}" "localhost:${VNC_PORT}" &
WEBSOCKIFY_PID=$!

# Start PCBnew
if [ -n "${PCB_FILE}" ]; then
    pcbnew "${PCB_FILE}" &
else
    pcbnew &
fi
PCBNEW_PID=$!

echo "VNC stack started:"
echo "  Xvfb       PID=${XVFB_PID}  display=:${DISPLAY_NUM}  resolution=${RESOLUTION}"
echo "  openbox    PID=${OPENBOX_PID}"
echo "  x11vnc     PID=${X11VNC_PID}  port=${VNC_PORT}"
echo "  websockify PID=${WEBSOCKIFY_PID}  ws_port=${WS_PORT}"
echo "  pcbnew     PID=${PCBNEW_PID}"
echo ""
echo "Access via WebSocket: ws://localhost:${WS_PORT}"
echo "Access via noVNC web: http://localhost:${WS_PORT}/vnc.html"

# Wait for PCBnew to exit — then cleanup triggers
wait "$PCBNEW_PID"
