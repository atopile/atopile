import os
import shutil
import subprocess
import sys
import textwrap
from functools import partial
from pathlib import Path
from typing import Callable

import pytest

from faebryk.libs.util import run_live

HERE = Path(__file__).parent
DEFAULT_CONFIG = HERE / "default_ato.yaml"


def exec_build(args: list[str], cwd: Path) -> tuple[str, str, subprocess.Popen]:
    return run_live(
        [sys.executable, "-m", "atopile", "build", *args],
        env={**os.environ, "NONINTERACTIVE": "1"},
        stdout=print,
        stderr=print,
        check=False,
        cwd=cwd,
    )


EXEC_T = Callable[[str, list[str]], tuple[str, str, subprocess.Popen]]


def dump_and_run(src: str, args: list[str], working_dir: Path):
    # Copy the default_ato.yaml to the tmpdir
    shutil.copy2(DEFAULT_CONFIG, working_dir / "ato.yaml")

    with open(working_dir / "app.ato", "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(src))

    return exec_build(args, working_dir)


@pytest.fixture
def build_app(tmpdir: Path):
    yield partial(dump_and_run, working_dir=tmpdir)
