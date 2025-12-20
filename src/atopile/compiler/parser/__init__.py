import logging
import shutil
import subprocess
from pathlib import Path

from faebryk.libs.util import (
    global_lock,
    has_uncommitted_changes,
    is_editable_install,
    run_live,
)

logger = logging.getLogger(__name__)


def check_for_recompile():
    if not is_editable_install():
        return

    THIS_DIR = Path(__file__).parent
    parser_files = THIS_DIR.rglob("Ato*")
    uncommitted_changes = has_uncommitted_changes(parser_files)
    # If we can't check git (e.g., not in a repo) or there are no uncommitted changes,
    # skip recompilation. Only recompile when we confirm there ARE uncommitted changes.
    if uncommitted_changes is None or not uncommitted_changes:
        return

    # binary provided by antlr4-tools python package
    if shutil.which("antlr4") is None:
        logger.warning("antlr-tools not found, did you run `uv sync --dev`?")
        return

    logger.warning("Recompiling ato grammar")

    # compile using antlr4 python package
    GRAMMAR_FILES = [
        "AtoLexer.g4",
        "AtoParser.g4",
    ]

    with global_lock(THIS_DIR / "antlr.lock", timeout_s=10):
        try:
            run_live(
                [
                    "antlr4",
                    "-long-messages",
                    "-visitor",
                    "-no-listener",
                    "-Dlanguage=Python3",
                    *GRAMMAR_FILES,
                ],
                cwd=THIS_DIR,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"ANTLR compilation failed:\n{e.stderr}")


check_for_recompile()
