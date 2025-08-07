import sys
from pathlib import Path

ROOT = Path(__file__).parent
BIN_DIR = ROOT / "zig-out" / "lib"
sys.path.append(str(BIN_DIR))


def compile():
    # Get Python include directory
    import subprocess
    import sysconfig

    python_include = sysconfig.get_paths()["include"]
    python_lib = f"python{sys.version_info.major}.{sys.version_info.minor}"

    output_file = BIN_DIR / "pyzig.so"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "zig",
        "build-lib",
        "src/python_ext.zig",
        "-dynamic",
        "-fPIC",
        "-O",
        "ReleaseFast",
        "-I",
        python_include,
        "-lc",
        f"-l{python_lib}",
        f"-femit-bin={output_file}",
    ]

    print(f"Building with command: {' '.join(cmd)}")
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=Path(__file__).parent
    )

    if result.returncode != 0:
        print(f"Build failed:\n{result.stderr}")
        raise RuntimeError("Failed to build Zig extension")

    print(f"Successfully built {output_file}")


compile()
from pyzig import *  # noqa: E402, F403
