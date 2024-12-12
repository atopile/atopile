import logging
from contextlib import contextmanager
from os import PathLike
from pathlib import Path

from antlr4 import CommonTokenStream, FileStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

from atopile.parser.AtoLexer import AtoLexer
from atopile.parser.AtoParser import AtoParser

from .errors import UserFileNotFoundError, UserSyntaxError

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

IMMEDIATE_RAISE = False


def error_factory(
    e: Exception, msg: str, offendingSymbol, line, column
) -> UserSyntaxError:
    from atopile.parse_utils import get_src_info_from_token

    error = UserSyntaxError(f"{str(e)} '{msg}'")

    src_path, src_line, src_col = get_src_info_from_token(offendingSymbol)
    error.src_path = src_path

    # hack, need to up these one line for some reason
    error.src_stop_line = src_line - 1
    error.src_stop_col = column

    error.src_line = line - 1
    error.src_col = src_col
    return error


class ErrorListenerConverter(ErrorListener):
    """Converts an error into an AtoSyntaxError."""

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e: Exception):
        raise error_factory(e, msg, offendingSymbol, line, column)


class ErrorListenerCollector(ErrorListenerConverter):
    """Collects errors into a list."""

    def __init__(self) -> None:
        self.errors = []
        super().__init__()

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e: Exception):
        self.errors.append(error_factory(e, msg, offendingSymbol, line, column))


def make_parser(src_stream: InputStream) -> AtoParser:
    """Make a parser from a stream."""
    lexer = AtoLexer(src_stream)
    stream = CommonTokenStream(lexer)
    parser = AtoParser(stream)

    return parser


def set_error_listener(parser: AtoParser, error_listener: ErrorListener) -> None:
    """Utility function to set the error listener on a parser."""
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)


@contextmanager
def defer_parser_errors(parser: AtoParser) -> None:
    """Defer errors from a parser until the end of the context manager."""
    if IMMEDIATE_RAISE:
        error_listener = ErrorListenerConverter()
    else:
        error_listener = ErrorListenerCollector()
    set_error_listener(parser, error_listener)

    yield

    if not IMMEDIATE_RAISE and error_listener.errors:
        raise ExceptionGroup("Errors caused parsing failure", error_listener.errors)


def parse_text_as_file(
    src_code: str, src_path: None | str | Path = None
) -> AtoParser.File_inputContext:
    """Parse a string as a file input."""
    input = InputStream(src_code)
    input.name = src_path
    parser = make_parser(input)
    with defer_parser_errors(parser):
        tree = parser.file_input()

    return tree


def parse_file(src_path: Path) -> AtoParser.File_inputContext:
    """Parse a file from a path."""
    input = FileStream(str(src_path), encoding="utf-8")
    input.name = src_path
    parser = make_parser(input)
    with defer_parser_errors(parser):
        tree = parser.file_input()

    return tree


class FileParser:
    """Parses a file."""

    def __init__(self) -> None:
        self.cache = {}

    def get_ast_from_file(self, src_origin: PathLike) -> AtoParser.File_inputContext:
        """Get the AST from a file."""

        src_origin_str = str(src_origin)
        src_origin_path = Path(src_origin)

        if src_origin_str not in self.cache:
            if not src_origin_path.exists():
                raise UserFileNotFoundError(src_origin_str)
            self.cache[src_origin_str] = parse_file(src_origin_path)

        return self.cache[src_origin_str]


parser = FileParser()
