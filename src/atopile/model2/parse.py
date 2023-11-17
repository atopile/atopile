import logging
from contextlib import contextmanager
from pathlib import Path

from antlr4 import CommonTokenStream, FileStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

from atopile.model2.errors import AtoSyntaxError
from atopile.parser.AtopileLexer import AtopileLexer
from atopile.parser.AtopileParser import AtopileParser

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class ErrorListenerConverter(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e: Exception):
        raise AtoSyntaxError.from_token(f"{str(e)} '{msg}'", offendingSymbol)


class ErrorListenerCollector(ErrorListenerConverter):
    def __init__(self) -> None:
        self.errors = []
        super().__init__()

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e: Exception):
        self.errors.append(AtoSyntaxError.from_token(f"{str(e)} '{msg}'", offendingSymbol))


def make_parser(src_stream: InputStream) -> AtopileParser:
    lexer = AtopileLexer(src_stream)
    stream = CommonTokenStream(lexer)
    parser = AtopileParser(stream)

    return parser


def set_error_listener(parser: AtopileParser, error_listener: ErrorListener) -> None:
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)


@contextmanager
def defer_parser_errors(parser: AtopileParser) -> None:
    error_listener = ErrorListenerCollector()
    set_error_listener(parser, error_listener)

    yield parser

    if error_listener.errors:
        raise ExceptionGroup("Errors caused parsing failure", error_listener.errors)


def parse_text_as_file(src_code: str, src_path: None | str | Path = None) -> AtopileParser.File_inputContext:
    """Parse a string as a file input."""
    input = InputStream(src_code)
    input.name = src_path
    parser = make_parser(input)
    with defer_parser_errors(parser):
        tree = parser.file_input()

    return tree


def parse_file(src_path: Path) -> AtopileParser.File_inputContext:
    """Parse a file from a path."""
    input = FileStream(str(src_path), encoding="utf-8")
    input.name = src_path
    parser = make_parser(input)
    with defer_parser_errors(parser):
        tree = parser.file_input()

    return tree
