"""
OS-level helpers for opening files and folders.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)


def open_with_system(path: Path) -> None:
    """
    Open a file or folder using the system default handler.
    """
    if sys.platform.startswith("darwin"):
        subprocess.run(["open", str(path)], check=False)
    elif os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def open_in_editor(path: Path, line: Optional[int] = None, column: Optional[int] = None) -> None:
    """
    Open a file in an editor if possible; fall back to system open.
    """
    code = shutil.which("code")
    if code:
        target = str(path)
        if line is not None:
            target = f"{target}:{line}"
            if column is not None:
                target = f"{target}:{column}"
        try:
            subprocess.run([code, "-g", target], check=False)
            return
        except Exception as e:
            log.debug(f"Failed to open with VS Code CLI: {e}")

    open_with_system(path)
