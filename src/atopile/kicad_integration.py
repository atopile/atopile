import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

from atopile.config import config

logger = logging.getLogger(__name__)


def find_kicad_executable() -> Optional[Path]:
    """Find the KiCad PCB editor executable."""
    possible_names = ["pcbnew", "kicad-pcbnew", "kicad"]

    for name in possible_names:
        try:
            result = subprocess.run(["which", name], capture_output=True, text=True)
            if result.returncode == 0:
                return Path(result.stdout.strip())
        except Exception:
            continue

    possible_paths = [
        "/usr/bin/pcbnew",
        "/usr/local/bin/pcbnew",
        "/Applications/KiCad/KiCad.app/Contents/MacOS/pcbnew",
        "C:\\Program Files\\KiCad\\bin\\pcbnew.exe",
    ]

    for path_str in possible_paths:
        path = Path(path_str)
        if path.exists():
            return path

    return None


def auto_open_kicad(pcb_layout_path: Path) -> bool:
    """
    Automatically open the PCB file in KiCad.

    Args:
        pcb_layout_path: Path to the .kicad_pcb file

    Returns:
        True if KiCad was opened successfully, False otherwise
    """
    if not config.build.auto_open_kicad:
        logger.debug("Auto-open KiCad is disabled")
        return False

    kicad_exe = find_kicad_executable()
    if not kicad_exe:
        logger.warning("KiCad executable not found, cannot auto-open PCB")
        return False

    if not pcb_layout_path.exists():
        logger.error(f"PCB file not found: {pcb_layout_path}")
        return False

    try:
        if sys.platform.startswith("darwin"):
            subprocess.Popen(["open", "-a", str(kicad_exe), str(pcb_layout_path)])
        elif sys.platform.startswith("win"):
            subprocess.Popen([str(kicad_exe), str(pcb_layout_path)])
        else:
            subprocess.Popen([str(kicad_exe), str(pcb_layout_path)])

        logger.info(f"Opened PCB in KiCad: {pcb_layout_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to open KiCad: {e}")
        return False


def get_pcb_file_for_build() -> Optional[Path]:
    """Get the PCB file path for the current build."""
    if config.build.paths.layout and config.build.paths.layout.exists():
        return config.build.paths.layout

    build_name = config.build.name
    possible_paths = [
        config.build.paths.output_base.parent / f"{build_name}.kicad_pcb",
        config.build.paths.output_base.parent
        / "layouts"
        / build_name
        / f"{build_name}.kicad_pcb",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None
