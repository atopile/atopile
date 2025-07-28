import contextlib
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

import pcbnew  # type: ignore
import wx as wx_module  # type: ignore

log = logging.getLogger(__name__)


# ATTENTION: RUNS IN PYTHON3.8


def run_ato(args: list[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Run the ato command with the given arguments."""
    executable = os.environ.get("ATOPILE_PYTHON")
    if not executable:
        raise RuntimeError("ATOPILE_PYTHON not set")
    cmd = [executable, "-m", "atopile"] + args
    try:
        out = subprocess.run(cmd, check=True, text=True, cwd=cwd, capture_output=True)
    except FileNotFoundError:
        log.error(f"Could not find Python executable: {executable}")

        message_box(
            "Could not find Python interpreter or atopile module. "
            "Please ensure atopile is installed and run 'ato configure' "
            "to set up the KiCad plugin environment.",
            "Pull Group Error",
            wx_module.OK | wx_module.ICON_ERROR,
        )
        raise

    log.info(f"Ran ato command: {cmd}")
    log.info(f"Output: {out.stdout}")
    log.info(f"Error: {out.stderr}")
    return out


def message_box(message: str, title: str, icon: int):
    """Show a message box."""
    wx = pcbnew.GetWXApp()
    if wx:
        wx_module.MessageBox(message, title, icon)
    else:
        log.warning("No wx application found")


@contextlib.contextmanager
def log_exceptions():
    try:
        yield
    except Exception as e:
        log.exception(e)
        raise
