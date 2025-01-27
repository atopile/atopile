import logging
from os import PathLike
from pathlib import Path

from antlr4 import CommonTokenStream, FileStream, InputStream, Token
from antlr4.error.ErrorListener import ErrorListener

from atopile.parser.AtoLexer import AtoLexer
from atopile.parser.AtoParser import AtoParser

from .errors import UserFileNotFoundError, UserSyntaxError

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class ErrorListenerConverter(ErrorListener):
    """Converts an error into an AtoSyntaxError."""

    def syntaxError(
        self,
        recognizer,
        offendingSymbol: Token,
        line: int,
        column: int,
        msg: str,
        e: Exception | None,
    ):
        if e is None:
            msg = msg
        else:
            msg = f"{str(e)} '{msg}'"

        input_stream: CommonTokenStream = recognizer.getInputStream()
        # This fill is required to get context past the offending symbol
        # to accurately report the error
        input_stream.fill()

        raise UserSyntaxError.from_tokens(
            input_stream, offendingSymbol, None, msg, markdown=False
        )


def make_parser(src_stream: InputStream) -> AtoParser:
    """Make a parser from a stream."""
    lexer = AtoLexer(src_stream)
    stream = CommonTokenStream(lexer)
    parser = AtoParser(stream)

    return parser


def parse_text_as_file(
    src_code: str, src_path: None | str | Path = None
) -> AtoParser.File_inputContext:
    """Parse a string as a file input."""
    input = InputStream(src_code)
    input.name = src_path
    parser = make_parser(input)

    parser.removeErrorListeners()
    parser.addErrorListener(ErrorListenerConverter())

    tree = parser.file_input()

    return tree


def parse_file(src_path: Path) -> AtoParser.File_inputContext:
    """Parse a file from a path."""
    input = FileStream(str(src_path), encoding="utf-8")
    input.name = src_path
    parser = make_parser(input)

    parser.removeErrorListeners()
    parser.addErrorListener(ErrorListenerConverter())

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
