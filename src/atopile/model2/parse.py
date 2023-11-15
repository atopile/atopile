import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext, contextmanager
from pathlib import Path
from typing import Iterable, Iterator

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener
from antlr4.ParserRuleContext import ParserRuleContext
from rich.progress import Progress

from atopile.parser.AtopileLexer import AtopileLexer
from atopile.parser.AtopileParser import AtopileParser
from atopile.utils import profile as profile_within
from atopile.model2.errors import AtoSyntaxError

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class ParserErrorListener(ErrorListener):
    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath
        self.errors = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errors.append(AtoSyntaxError(f"Syntax error: '{msg}'", self.filepath, line, column))


@contextmanager
def error_deferred_parser(src_path: str | Path, src_code: str) -> Iterator[AtopileParser]:
    error_listener = ParserErrorListener(src_path)

    input = InputStream(src_code)

    lexer = AtopileLexer(input)
    stream = CommonTokenStream(lexer)
    parser = AtopileParser(stream)
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)

    yield parser

    if error_listener.errors:
        raise ExceptionGroup(f"Syntax errors caused parsing of {str(src_path)} to fail", error_listener.errors)


def parse_text(src_path: str | Path, src_code: str) -> ParserRuleContext:
    with error_deferred_parser(src_path, src_code) as parser:
        tree = parser.file_input()

    return tree


def parse_file(file_path: Path) -> ParserRuleContext:
    with file_path.open("r", encoding="utf-8") as f:
        return parse_text(file_path, f.read())


def parse(
    file_paths: Iterable[Path],
    profile: bool = False,
    max_workers: int = 4,
) -> dict[Path, ParserRuleContext]:
    """
    Parse all the files in the given paths, returning a map of their trees

    FIXME: handle exceptions causing syntax errors better

    FIXME: accept logger as argument

    FIXME: this is currently heavily GIL bound.
        Unfortunately, the simple option of using multiprocessing is not available
        because the antlr4 library is not pickleable.
    """
    log.info("Parsing tree")

    profiler_context = profile_within(log) if profile else nullcontext()

    path_to_tree: dict[Path, ParserRuleContext] = {}

    log.info("Searching...")
    file_paths = list(file_paths)

    with (
        profiler_context,
        ThreadPoolExecutor(max_workers=max_workers) as executor,
        Progress() as progress,
    ):
        progress_task = progress.add_task("Parsing...", total=len(file_paths))

        for path, tree in zip(file_paths, executor.map(parse_text, file_paths)):
            progress.update(progress_task, advance=1)
            path_to_tree[path] = tree
            log.info(f"Finished {str(path)}")

    return path_to_tree
