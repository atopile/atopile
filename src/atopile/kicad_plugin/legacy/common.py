import contextlib
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

import wx as wx_module  # type: ignore

# ATTENTION: RUNS IN PYTHON3.8

LOG_FILE = (Path(__file__).parent / "log.log").expanduser().absolute()
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
formatter = logging.Formatter("%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
file_handler = logging.FileHandler(str(LOG_FILE), "w", "utf-8")
file_handler.setFormatter(formatter)


def setup_logger(module_name: str):
    log = logging.getLogger(module_name)
    log.addHandler(file_handler)
    log.setLevel(logging.INFO)
    return log


log = setup_logger(__name__)


def run_ato(args: list[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Run the ato command with the given arguments."""
    executable = os.environ.get("ATOPILE_PYTHON")
    if not executable:
        raise RuntimeError("ATOPILE_PYTHON not set")
    cmd = [executable, "-m", "atopile"] + args
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONEXECUTABLE", None)
    try:
        out = subprocess.run(
            cmd, check=True, text=True, cwd=cwd, capture_output=True, env=env
        )
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
    log.info(f"stdo: {out.stdout}")
    log.info(f"stde: {out.stderr}")
    return out


def message_box(message: str, title: str, icon: int):
    """Show a message box."""
    wx = wx_module.GetApp()
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
