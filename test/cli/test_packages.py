import os
import re
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from atopile.cli.package import _PackageValidators
from atopile.errors import UserBadParameterError
from faebryk.libs.util import repo_root as _repo_root
from faebryk.libs.util import run_live


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape codes and Rich markup tags from text."""
    # Strip ANSI escape codes
    text = re.sub(r"\x1b\[[0-9;]*m", "", text)
    # Strip Rich markup tags like [green], [/green], [/], [bold red], etc.
    text = re.sub(r"\[/?[a-zA-Z_ ]*\]", "", text)
    return text


# Get the examples directory relative to this test file
EXAMPLES_DIR = _repo_root() / "examples"


@pytest.mark.parametrize("package", ["atopile/addressable-leds"])
def test_install_package(package: str, tmp_path: Path):
    example_copy = tmp_path / "example"

    shutil.copytree(
        EXAMPLES_DIR / "quickstart",
        example_copy,
        ignore=lambda src, names: [".ato", "build", "standalone"],
    )

    stdout, stderr, _ = run_live(
        [sys.executable, "-m", "atopile", "add", package],
        env={**os.environ, "NONINTERACTIVE": "1"},
        cwd=example_copy,
        stdout=print,
        stderr=print,
    )

    # Check combined output (FBRK_LOG_FMT affects which stream logs go to)
    # Strip ANSI codes and Rich markup since output may not be rendered
    combined = _strip_ansi(stdout + stderr)
    assert f"+ {package}@" in combined
    assert "Done!" in combined


# ---------------------------------------------------------------------------
# Tests for verify_unused_and_duplicate_imports
# ---------------------------------------------------------------------------


def _make_config(root: Path):
    """Create a minimal mock config with config.project.paths.root = root."""
    return SimpleNamespace(project=SimpleNamespace(paths=SimpleNamespace(root=root)))


def _write_ato(root: Path, filename: str, content: str) -> Path:
    f = root / filename
    f.write_text(content, encoding="utf-8")
    return f


class TestVerifyUnusedAndDuplicateImports:
    """Tests for _PackageValidators.verify_unused_and_duplicate_imports."""

    def test_used_import_no_error(self, tmp_path: Path):
        _write_ato(
            tmp_path,
            "test.ato",
            "import Resistor\n\nmodule Test:\n    r = new Resistor\n",
        )
        config = _make_config(tmp_path)
        _PackageValidators.verify_unused_and_duplicate_imports(config)

    def test_unused_import(self, tmp_path: Path):
        _write_ato(
            tmp_path,
            "test.ato",
            "import Resistor\n\nmodule Test:\n    pass\n",
        )
        config = _make_config(tmp_path)
        with pytest.raises(UserBadParameterError, match="Unused imports"):
            _PackageValidators.verify_unused_and_duplicate_imports(config)

    def test_duplicate_import(self, tmp_path: Path):
        _write_ato(
            tmp_path,
            "test.ato",
            "import Resistor\nimport Resistor\n\nmodule Test:\n    r = new Resistor\n",
        )
        config = _make_config(tmp_path)
        with pytest.raises(UserBadParameterError, match="Duplicate imports"):
            _PackageValidators.verify_unused_and_duplicate_imports(config)

    def test_unused_and_duplicate_import(self, tmp_path: Path):
        """Two identical imports with no other usage: the name count is 2
        (one per import line) so it's only flagged as duplicate, not unused."""
        _write_ato(
            tmp_path,
            "test.ato",
            "import Resistor\nimport Resistor\n\nmodule Test:\n    pass\n",
        )
        config = _make_config(tmp_path)
        with pytest.raises(UserBadParameterError, match="Duplicate imports"):
            _PackageValidators.verify_unused_and_duplicate_imports(config)

    def test_commented_import_ignored(self, tmp_path: Path):
        """Imports in comments (# import Foo) should not be detected."""
        _write_ato(
            tmp_path,
            "test.ato",
            "# import UnusedModule\nimport Resistor\n\nmodule Test:\n    "
            "r = new Resistor\n",
        )
        config = _make_config(tmp_path)
        _PackageValidators.verify_unused_and_duplicate_imports(config)

    def test_commented_from_import_ignored(self, tmp_path: Path):
        """from-imports in comments should not be detected."""
        _write_ato(
            tmp_path,
            "test.ato",
            '# from "lib.ato" import UnusedModule\nimport Resistor\n\nmodule Test:\n'
            "    r = new Resistor\n",
        )
        config = _make_config(tmp_path)
        _PackageValidators.verify_unused_and_duplicate_imports(config)

    def test_substring_not_counted_as_usage(self, tmp_path: Path):
        """'Module' should not be considered used because 'ModuleExtended' exists."""
        _write_ato(
            tmp_path,
            "test.ato",
            "import Module\n\nmodule Test:\n    m = new ModuleExtended\n",
        )
        config = _make_config(tmp_path)
        with pytest.raises(UserBadParameterError, match="Unused imports"):
            _PackageValidators.verify_unused_and_duplicate_imports(config)

    def test_superstring_not_counted_as_usage(self, tmp_path: Path):
        """'ModuleExtended' should not be considered used because 'Module' exists."""
        _write_ato(
            tmp_path,
            "test.ato",
            "import ModuleExtended\n\nmodule Test:\n    m = new Module\n",
        )
        config = _make_config(tmp_path)
        with pytest.raises(UserBadParameterError, match="Unused imports"):
            _PackageValidators.verify_unused_and_duplicate_imports(config)

    def test_multi_module_import_first_checked(self, tmp_path: Path):
        """In 'import A, B', at least the first name (A) should be checked."""
        _write_ato(
            tmp_path,
            "test.ato",
            "import Resistor, Capacitor\n\nmodule Test:\n    pass\n",
        )
        config = _make_config(tmp_path)
        with pytest.raises(UserBadParameterError, match="Unused imports"):
            _PackageValidators.verify_unused_and_duplicate_imports(config)

    def test_from_import_used_no_error(self, tmp_path: Path):
        _write_ato(
            tmp_path,
            "test.ato",
            'from "lib.ato" import Resistor\n\nmodule Test:\n    r = new Resistor\n',
        )
        config = _make_config(tmp_path)
        _PackageValidators.verify_unused_and_duplicate_imports(config)

    def test_from_import_unused(self, tmp_path: Path):
        _write_ato(
            tmp_path,
            "test.ato",
            'from "lib.ato" import Resistor\n\nmodule Test:\n    pass\n',
        )
        config = _make_config(tmp_path)
        with pytest.raises(UserBadParameterError, match="Unused imports"):
            _PackageValidators.verify_unused_and_duplicate_imports(config)

    def test_from_import_duplicate(self, tmp_path: Path):
        _write_ato(
            tmp_path,
            "test.ato",
            'from "lib.ato" import Resistor\nfrom "lib.ato" import Resistor\n\nmodule '
            "Test:\n    r = new Resistor\n",
        )
        config = _make_config(tmp_path)
        with pytest.raises(UserBadParameterError, match="Duplicate imports"):
            _PackageValidators.verify_unused_and_duplicate_imports(config)

    def test_mixed_import_and_from_import(self, tmp_path: Path):
        """Both import styles used together, all used — no error."""
        _write_ato(
            tmp_path,
            "test.ato",
            'import Resistor\nfrom "lib.ato" import Capacitor\n\nmodule Test:\n    '
            "r = new Resistor\n    c = new Capacitor\n",
        )
        config = _make_config(tmp_path)
        _PackageValidators.verify_unused_and_duplicate_imports(config)

    def test_no_ato_files(self, tmp_path: Path):
        """No .ato files in the project — should pass without error."""
        config = _make_config(tmp_path)
        _PackageValidators.verify_unused_and_duplicate_imports(config)

    def test_no_imports_no_error(self, tmp_path: Path):
        _write_ato(
            tmp_path,
            "test.ato",
            "module Test:\n    pass\n",
        )
        config = _make_config(tmp_path)
        _PackageValidators.verify_unused_and_duplicate_imports(config)


class TestVerifyNoCommaSeparatedImports:
    """Tests for _PackageValidators.verify_no_comma_separated_imports."""

    def test_single_import_no_error(self, tmp_path: Path):
        _write_ato(tmp_path, "test.ato", "import Resistor\n")
        config = _make_config(tmp_path)
        _PackageValidators.verify_no_comma_separated_imports(config)

    def test_single_from_import_no_error(self, tmp_path: Path):
        _write_ato(tmp_path, "test.ato", 'from "lib.ato" import Resistor\n')
        config = _make_config(tmp_path)
        _PackageValidators.verify_no_comma_separated_imports(config)

    def test_comma_separated_import_rejected(self, tmp_path: Path):
        _write_ato(tmp_path, "test.ato", "import Resistor, Capacitor\n")
        config = _make_config(tmp_path)
        with pytest.raises(UserBadParameterError, match="Comma-separated imports"):
            _PackageValidators.verify_no_comma_separated_imports(config)

    def test_comma_separated_import_three_names(self, tmp_path: Path):
        _write_ato(tmp_path, "test.ato", "import A, B, C\n")
        config = _make_config(tmp_path)
        with pytest.raises(UserBadParameterError, match="Comma-separated imports"):
            _PackageValidators.verify_no_comma_separated_imports(config)

    def test_comma_separated_from_import_rejected(self, tmp_path: Path):
        _write_ato(tmp_path, "test.ato", 'from "lib.ato" import Resistor, Capacitor\n')
        config = _make_config(tmp_path)
        with pytest.raises(UserBadParameterError, match="Comma-separated imports"):
            _PackageValidators.verify_no_comma_separated_imports(config)

    def test_commented_comma_import_ignored(self, tmp_path: Path):
        _write_ato(tmp_path, "test.ato", "# import Resistor, Capacitor\n")
        config = _make_config(tmp_path)
        _PackageValidators.verify_no_comma_separated_imports(config)

    def test_separate_imports_no_error(self, tmp_path: Path):
        """Multiple separate import statements are fine."""
        _write_ato(tmp_path, "test.ato", "import Resistor\nimport Capacitor\n")
        config = _make_config(tmp_path)
        _PackageValidators.verify_no_comma_separated_imports(config)

    def test_no_ato_files(self, tmp_path: Path):
        config = _make_config(tmp_path)
        _PackageValidators.verify_no_comma_separated_imports(config)

    def test_error_message_contains_statement(self, tmp_path: Path):
        _write_ato(tmp_path, "test.ato", "import Resistor, Capacitor\n")
        config = _make_config(tmp_path)
        with pytest.raises(UserBadParameterError) as exc_info:
            _PackageValidators.verify_no_comma_separated_imports(config)
        assert "import Resistor, Capacitor" in str(exc_info.value)
