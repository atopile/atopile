import logging
from os import PathLike
from pathlib import Path

from antlr4 import CommonTokenStream, FileStream, InputStream, Token
from antlr4.error.ErrorListener import ErrorListener

from atopile.compiler.parser.AtoLexer import AtoLexer
from atopile.compiler.parser.AtoParser import AtoParser
from atopile.errors import UserFileNotFoundError, UserSyntaxError

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def _detect_name_starting_with_number(
    offending_symbol: Token,
    token_stream: CommonTokenStream,
) -> str | None:
    """
    Detect when a user tries to use an identifier starting with a number.

    ANTLR tokenizes "68f47" as INTEGER("68") + NAME("f47"), producing a confusing
    "extraneous input" error. This function detects that pattern and returns
    the attempted identifier name, or None if not detected.
    """
    next_token_index = offending_symbol.tokenIndex + 1
    tokens = token_stream.tokens

    if next_token_index < len(tokens):
        next_token = tokens[next_token_index]
        # Check if next token is NAME immediately following the number (no whitespace)
        if (
            next_token.type == AtoLexer.NAME
            and next_token.line == offending_symbol.line
            and next_token.column
            == offending_symbol.column + len(offending_symbol.text)
        ):
            return offending_symbol.text + next_token.text

    # Just a number where a name was expected
    return offending_symbol.text


class ErrorListenerConverter(ErrorListener):
    """Converts an error into an AtoSyntaxError."""

    def __init__(self):
        super().__init__()
        self.errors: list[UserSyntaxError] = []

    def syntaxError(
        self,
        recognizer,
        offendingSymbol: Token,
        line: int,
        column: int,
        msg: str,
        e: Exception | None,
    ):
        if e is not None and e.args != (None,):
            msg = f"{e} {msg}"

        input_stream: CommonTokenStream = recognizer.getInputStream()
        # This fill is required to get context past the offending symbol
        # to accurately report the error
        input_stream.fill()

        # Detect identifier starting with a number (e.g., "68f47 = new Electrical")
        if (
            offendingSymbol is not None
            and offendingSymbol.type in (AtoLexer.NUMBER, AtoLexer.INTEGER)
            and "expecting" in msg
            and "NAME" in msg
        ):
            name = _detect_name_starting_with_number(offendingSymbol, input_stream)
            msg = f"Invalid name `{name}`: names cannot start with a number."

        self.errors.append(
            UserSyntaxError.from_tokens(
                input_stream, offendingSymbol, None, msg, markdown=False
            )
        )


def make_parser(src_stream: InputStream) -> tuple[AtoParser, ErrorListenerConverter]:
    """Make a parser from a stream."""
    lexer = AtoLexer(src_stream)
    stream = CommonTokenStream(lexer)
    parser = AtoParser(stream)

    parser.removeErrorListeners()
    listener = ErrorListenerConverter()
    parser.addErrorListener(listener)

    return parser, listener


def _parse_input(
    input: InputStream, raise_multiple_errors: bool = False
) -> AtoParser.File_inputContext:
    parser, listener = make_parser(input)
    tree = parser.file_input()

    match listener.errors:
        case []:
            return tree
        case [error]:
            raise error
        case errors:
            if raise_multiple_errors:
                raise ExceptionGroup("Multiple syntax errors found", errors)

            raise errors[0]


def parse_text_as_file(
    src_code: str,
    src_path: None | str | Path = None,
    raise_multiple_errors: bool = False,
) -> AtoParser.File_inputContext:
    """Parse a string as a file input."""
    input = InputStream(src_code)
    input.name = str(src_path)
    return _parse_input(input, raise_multiple_errors=raise_multiple_errors)


def parse_file(
    src_path: str | Path, raise_multiple_errors: bool = False
) -> AtoParser.File_inputContext:
    """Parse a file from a path."""
    input = FileStream(str(src_path), encoding="utf-8")
    input.name = str(src_path)
    return _parse_input(input, raise_multiple_errors=raise_multiple_errors)


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

    def get_ast_from_text(
        self, src_code: str, src_path: Path | None = None
    ) -> AtoParser.File_inputContext:
        """Get the AST from a string."""
        # TODO: caching
        return parse_text_as_file(src_code, src_path, raise_multiple_errors=True)


parser = FileParser()
