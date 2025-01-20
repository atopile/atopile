import logging
import sys
from pathlib import Path
from typing import Iterable

from git import Repo

from faebryk.libs.util import AUTO_RECOMPILE, is_editable_install, run_live

logger = logging.getLogger(__name__)


if is_editable_install() and AUTO_RECOMPILE.get():

    def has_uncommitted_changes(files: Iterable[str | Path]) -> bool:
        """Check if any of the given files have uncommitted changes."""
        try:
            repo = Repo(search_parent_directories=True)
            diff_index = repo.index.diff(None)  # Get uncommitted changes

            # Convert all files to Path objects for consistent comparison
            files = [Path(f).resolve() for f in files]
            repo_root = Path(repo.working_dir)

            # Check if any of the files have changes
            for diff in diff_index:
                diff_path = (repo_root / diff.a_path).resolve()
                if diff_path in files:
                    return True

            return False
        except Exception:
            # If we can't check git status (not a git repo, etc), assume we don't need to recompile # noqa: E501  # pre-existing
            return False

    SAUCY_FILES = [
        "AtoParser.g4",
        "AtoLexer.g4",
        "AtoParserBase.py",
        "AtoLexerBase.py",
    ]
    THIS_DIR = Path(__file__).parent

    if has_uncommitted_changes(THIS_DIR / f for f in SAUCY_FILES):
        logger.warning("Recompiling ANTLR4 grammars due to changes in grammar files")
        bin_dir = Path(sys.executable).parent
        run_live(
            [
                bin_dir / "antlr4",
                "-visitor",
                "-no-listener",
                "-Dlanguage=Python3",
                "AtoLexer.g4",
                "AtoParser.g4",
            ],
            cwd=THIS_DIR,
        )
