import hashlib
import importlib.util
import os
import shutil
import stat
import sys
import uuid
from pathlib import Path
from types import ModuleType


def _hash_string(path: str) -> str:
    """Spits out a uuid in hex from a string"""
    path_as_bytes = path.encode("utf-8")
    hashed_path = hashlib.blake2b(path_as_bytes, digest_size=16).digest()
    return str(uuid.UUID(bytes=hashed_path))


def robustly_rm_dir(path: Path) -> None:
    """Remove a directory and all its contents."""

    def remove_readonly(func, path, excinfo):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    shutil.rmtree(path, onerror=remove_readonly)
