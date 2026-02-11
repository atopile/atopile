#!/bin/bash
set -euo pipefail

# Start a VNC-accessible PCBnew session inside the Docker container.
# Usage: start-pcbnew-vnc.sh [path/to/file.kicad_pcb]
#
# Components launched:
#   Xorg+dummy  – X server with dummy video driver on :99 (supports RANDR resize)
#   openbox     – lightweight window manager (PCBnew needs one for dialogs/menus)
#   x11vnc      – VNC server watching :99
#   websockify  – WebSocket-to-TCP proxy (ws://6080 → tcp://5900)
#   pcbnew      – KiCad PCB editor

PCB_FILE="${1:-}"
DISPLAY_NUM=99
VNC_PORT=5900
WS_PORT=6080

export DISPLAY=:${DISPLAY_NUM}

# Set GTK theme to match VS Code dark/light mode
# KICAD_DARK_MODE=1 → dark, KICAD_DARK_MODE=0 → light (default: dark)
if [ "${KICAD_DARK_MODE:-1}" = "0" ]; then
    export GTK_THEME=Adwaita
else
    export GTK_THEME=Adwaita:dark
fi

# Cleanup function
cleanup() {
    kill "$PCBNEW_PID" "$WEBSOCKIFY_PID" "$X11VNC_PID" "$OPENBOX_PID" "$XORG_PID" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Write xorg.conf for the dummy video driver
# Virtual 3840 2160 sets the maximum framebuffer; actual resolution is set at runtime via xrandr
XORG_CONF="/tmp/xorg-dummy.conf"
cat > "${XORG_CONF}" << 'XCONF'
Section "ServerFlags"
    Option "AutoAddDevices" "false"
    Option "AutoEnableDevices" "false"
    Option "DontVTSwitch" "true"
EndSection

Section "Device"
    Identifier "dummy"
    Driver "dummy"
    VideoRam 256000
EndSection

Section "Screen"
    Identifier "screen"
    Device "dummy"
    DefaultDepth 24
    SubSection "Display"
        Depth 24
        Virtual 3840 2160
    EndSubSection
EndSection
XCONF

# Start Xorg with dummy driver (supports full RANDR for dynamic resize)
Xorg -noreset +extension RANDR -ac -config "${XORG_CONF}" ":${DISPLAY_NUM}" &
XORG_PID=$!
sleep 1

# Configure openbox: no decorations, auto-maximize all windows
OPENBOX_CONF_DIR="${HOME}/.config/openbox"
mkdir -p "${OPENBOX_CONF_DIR}"
cat > "${OPENBOX_CONF_DIR}/rc.xml" << 'OBXML'
<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
  <theme><titleLayout></titleLayout></theme>
  <applications>
    <application class="*">
      <decor>no</decor>
      <maximized>yes</maximized>
    </application>
  </applications>
</openbox_config>
OBXML

# Start openbox window manager
openbox --config-file "${OPENBOX_CONF_DIR}/rc.xml" &
OPENBOX_PID=$!

# Start x11vnc — localhost only, no password, shared access
x11vnc -display ":${DISPLAY_NUM}" -nopw -listen localhost -forever -shared -rfbport "${VNC_PORT}" \
  -noxdamage \
  -noxrecord \
  -allinput \
  -defer 0 \
  -wait 5 \
  -nonap \
  -xrandr newfbsize &
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
echo "  Xorg       PID=${XORG_PID}  display=:${DISPLAY_NUM}  driver=dummy"
echo "  openbox    PID=${OPENBOX_PID}"
echo "  x11vnc     PID=${X11VNC_PID}  port=${VNC_PORT}"
echo "  websockify PID=${WEBSOCKIFY_PID}  ws_port=${WS_PORT}"
echo "  pcbnew     PID=${PCBNEW_PID}"
echo ""
echo "Access via WebSocket: ws://localhost:${WS_PORT}"
echo "Access via noVNC web: http://localhost:${WS_PORT}/vnc.html"

# Wait for PCBnew to exit — then cleanup triggers
wait "$PCBNEW_PID"
