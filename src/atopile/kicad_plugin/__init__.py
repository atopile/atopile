import logging
from pathlib import Path

from . import pullgroup, pushgroup, reloadgroup  # noqa: F401

LOG_FILE = (Path(__file__).parent / "log.log").expanduser().absolute()
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

log = logging.getLogger(__name__)
formatter = logging.Formatter("%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
file_handler = logging.FileHandler(str(LOG_FILE), "w", "utf-8")
file_handler.setFormatter(formatter)
log.addHandler(file_handler)
log.setLevel(logging.DEBUG)
