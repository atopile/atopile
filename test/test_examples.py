import os
import shutil
import sys
from pathlib import Path
from subprocess import CalledProcessError

import pathvalidate
import pytest

from faebryk.libs.util import repo_root as _repo_root
from faebryk.libs.util import robustly_rm_dir, run_live

# Get the examples directory relative to this test file
EXAMPLES_DIR = _repo_root() / "examples"

FABLL_EXAMPLES = [p for p in EXAMPLES_DIR.glob("*.py") if p.is_file()]
ATO_EXAMPLES = [p for p in EXAMPLES_DIR.glob("*.ato") if p.is_file()]

XFAILURES = {
    "ch2_5_signal_processing": "Need more powerful expression reordering",  # TODO
    "ch1_2_good_voltage_divider": "Need more powerful expression reordering",  # TODO
}


@pytest.mark.parametrize(
    "example",
    (
        pytest.param(example, marks=pytest.mark.xfail(reason=reason))
        if (reason := XFAILURES.get(example.stem))
        else example
        for example in FABLL_EXAMPLES + ATO_EXAMPLES
    ),
    ids=lambda p: p.stem,
)
@pytest.mark.not_in_ci
def test_examples_build(
    example: Path, tmp_path: Path, repo_root: Path, request: pytest.FixtureRequest
):
    assert example.exists()

    example_copy = tmp_path / example.name
    example_copy.write_text(example.read_text())
    example = example_copy

    # Copy dependencies to the tmp dir directly because standalone mode doens't include
    example_modules = repo_root / "test" / "common" / "resources" / ".ato" / "modules"
    for item in example_modules.glob("*"):
        if item.is_dir():
            shutil.copytree(item, tmp_path / item.name)
        else:
            shutil.copy(item, tmp_path / item.name)

    # Make the noise
    try:
        run_live(
            [
                sys.executable,
                "-m",
                "atopile",
                "build",
                "--standalone",
                f"{example}:App",
            ],
            env={**os.environ, "NONINTERACTIVE": "1"},
            cwd=tmp_path,
            stdout=print,
            stderr=print,
        )

    # If the build fails, save the artifacts and raise
    except CalledProcessError:
        artifact_path = (
            _repo_root()
            / "artifacts"
            / pathvalidate.sanitize_filename(str(request.node.name))
        )
        if artifact_path.exists():
            robustly_rm_dir(artifact_path)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(tmp_path, artifact_path, ignore=shutil.ignore_patterns(".git"))

        raise
