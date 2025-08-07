import logging
import sys
from pathlib import Path

from faebryk.libs.util import debug_perf, global_lock, run_live

logger = logging.getLogger(__name__)

_thisdir = Path(__file__).parent
_build_dir = _thisdir / "zig-out" / "lib"


@debug_perf
def compile_zig():
    # Get Python include directory
    import sysconfig

    python_include = sysconfig.get_paths()["include"]
    python_lib = f"python{sys.version_info.major}.{sys.version_info.minor}"

    zig_cmd = [sys.executable, "-m", "ziglang"]

    # Use zig build system with Python configuration
    cmd = [
        *zig_cmd,
        "build",
        "python-ext",
        "-Doptimize=ReleaseFast",
        f"-Dpython-include={python_include}",
        f"-Dpython-lib={python_lib}",
    ]

    logger.info(f"Building with command: {' '.join(cmd)}")
    with global_lock(_build_dir / "lock", timeout_s=60):
        run_live(cmd, cwd=Path(__file__).parent)

    if not (_build_dir / "pyzig.so").exists():
        raise RuntimeError("Failed to build Zig extension")


def load():
    sys.path.append(str(_build_dir))


compile_zig()
load()

from pyzig import *  # type: ignore # noqa: E402, F403
