import os
import shutil
import stat
from pathlib import Path


def robustly_rm_dir(path: Path) -> None:
    """Remove a directory and all its contents."""

    def remove_readonly(func, path, excinfo):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    shutil.rmtree(path, onerror=remove_readonly)
