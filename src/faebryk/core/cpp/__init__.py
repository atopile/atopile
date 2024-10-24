# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import pathlib
import shutil
import site
from typing import Callable

logger = logging.getLogger(__name__)


# Check if installed as editable
def is_editable_install():
    site_packages = site.getsitepackages()
    return not any((pathlib.Path(sp) / "faebryk").exists() for sp in site_packages)


def compile_and_load():
    """
    Forces C++ to compile into faebryk_core_cpp_editable module which is then loaded
    into _cpp.
    """
    import subprocess
    import sys

    cpp_dir = pathlib.Path(__file__).parent
    build_dir = cpp_dir / "build"

    # check for cmake binary existing
    if not shutil.which("cmake"):
        raise RuntimeError(
            "cmake not found, needed for compiling c++ code in editable mode"
        )

    pybind11_dir = subprocess.check_output(
        ["python", "-m", "pybind11", "--cmakedir"],
        text=True,
    ).strip()

    # force recompile
    # subprocess.run(["rm", "-rf", str(build_dir)], check=True)

    subprocess.run(
        [
            "cmake",
            "-S",
            str(cpp_dir),
            "-B",
            str(build_dir),
            "-DEDITABLE=1",
            f"-DCMAKE_PREFIX_PATH={pybind11_dir}",
        ],
        check=True,
    )
    subprocess.run(
        [
            "cmake",
            "--build",
            str(build_dir),
        ],
        check=True,
    )

    if not build_dir.exists():
        raise RuntimeError("build directory not found")

    sys.path.append(str(build_dir))
    global _cpp
    import faebryk_core_cpp_editable as _cpp  # type: ignore


if is_editable_install():
    logger.warning("faebryk is installed as editable package, compiling c++ code")
    compile_and_load()
else:
    # check whether module is available
    try:
        import faebryk_core_cpp as _cpp  # type: ignore # noqa: E402
    except ImportError:
        logger.warning("faebryk_core_cpp module not found, assuming editable mode")
        compile_and_load()


# Re-export c++ with type hints
add: Callable[[int, int], int] = _cpp.add
