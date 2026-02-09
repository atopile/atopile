#!/bin/bash
set -e

WORKSPACE="${HOME}/workspace"
DEFAULT_WORKSPACE="/tmp/default-workspace"

# If workspace is empty (e.g. fresh volume mount), seed it with the example project
if [ -d "${DEFAULT_WORKSPACE}" ] && [ -z "$(ls -A "${WORKSPACE}" 2>/dev/null)" ]; then
    echo "[web-ide] Initializing workspace with example project..."
    cp -r "${DEFAULT_WORKSPACE}/." "${WORKSPACE}/"
fi

# Ensure uv symlink exists at the extension-managed globalStorage path.
# The User data dir may be volume-mounted, so recreate this on every startup.
# Runtime data dir is $HOME/.openvscode-server/data/, NOT $OPENVSCODE_SERVER_ROOT/data/
UV_SYMLINK_DIR="${HOME}/.openvscode-server/data/User/globalStorage/atopile.atopile/uv-bin"
mkdir -p "${UV_SYMLINK_DIR}"
ln -sf /usr/local/bin/uv "${UV_SYMLINK_DIR}/uv"

echo "[web-ide] atopile $(ato --version 2>/dev/null || echo 'not found')"

# Install the atopile KiCad plugin for PCBnew.
# 1) Pre-create the plugin dir so get_plugin_paths() can discover it.
# 2) Run configure.setup() to write atopile.py loader + enable IPC API.
# 3) Symlink into ~/.config/kicad/ where KiCad's SETTINGS_MANAGER actually looks.
KICAD_DATA_PLUGINS="${HOME}/.local/share/kicad/9.0/scripting/plugins"
KICAD_CONFIG_PLUGINS="${HOME}/.config/kicad/9.0/scripting/plugins"
mkdir -p "${KICAD_DATA_PLUGINS}"
"${HOME}/.local/share/uv/tools/atopile/bin/python" -c "from atopile.cli.configure import setup; setup()" 2>/dev/null || true
if [ -f "${KICAD_DATA_PLUGINS}/atopile.py" ] && [ ! -e "${KICAD_CONFIG_PLUGINS}" ]; then
    mkdir -p "$(dirname "${KICAD_CONFIG_PLUGINS}")"
    ln -sf "${KICAD_DATA_PLUGINS}" "${KICAD_CONFIG_PLUGINS}"
    echo "[web-ide] KiCad plugin installed"
fi

# Pre-configure KiCad to skip first-run dialogs (data collection, update check, etc.)
KICAD_CFG_DIR="${HOME}/.config/kicad/9.0"
"${HOME}/.local/share/uv/tools/atopile/bin/python" - <<'PYEOF'
import json, pathlib, os

cfg_dir = pathlib.Path(os.environ["HOME"]) / ".config/kicad/9.0"
cfg_dir.mkdir(parents=True, exist_ok=True)

# Patch kicad_common.json — suppress all first-run dialogs
common_path = cfg_dir / "kicad_common.json"
if common_path.exists():
    common = json.loads(common_path.read_text())
else:
    common = {"meta": {"filename": "kicad_common.json", "version": 3}}

common.setdefault("do_not_show_again", {})
common["do_not_show_again"]["data_collection_prompt"] = True
common["do_not_show_again"]["update_check_prompt"] = True
common["do_not_show_again"]["env_var_overwrite_warning"] = True
common["do_not_show_again"]["scaled_3d_models_warning"] = True
common["do_not_show_again"]["zone_fill_warning"] = True

# Enable KiCad IPC API server so `reload_pcb()` can tell PCBnew to reload via socket
common.setdefault("api", {})
common["api"]["enable_server"] = True

common_path.write_text(json.dumps(common, indent=2))

# Create pcbnew.json if missing — marks PCBnew as already-configured
pcbnew_path = cfg_dir / "pcbnew.json"
if not pcbnew_path.exists():
    pcbnew_path.write_text(json.dumps({
        "meta": {"filename": "pcbnew", "version": 2},
        "printing": {"enabled": False}
    }, indent=2))

# Copy default library tables if missing — prevents KiCad first-run lib wizard
import shutil
for lib_table in ("fp-lib-table", "sym-lib-table"):
    dest = cfg_dir / lib_table
    src = pathlib.Path("/usr/share/kicad/template") / lib_table
    if not dest.exists() and src.exists():
        shutil.copy2(src, dest)

PYEOF

echo "[web-ide] Starting OpenVSCode Server..."

# Exec into OpenVSCode Server (replaces this shell process)
exec "${OPENVSCODE_SERVER_ROOT}/bin/openvscode-server" "$@"
