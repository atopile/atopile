import logging
from textwrap import dedent

from antlr4 import InputStream

from atopile.model2.parse import ErrorListenerConverter, make_parser, set_error_listener
from atopile.parser.AtopileParser import AtopileParser

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def parser_from_src_code(src_code: str) -> AtopileParser:
    """
    Helper function to parse ato source code, returning a parser object.

    It first dedents the code and removes leading and trailing whitespace,
    so multi-line strings can be used.

    This is useful for sandboxes and testing.
    """
    input = InputStream(dedent(src_code).strip())
    parser = make_parser(input)
    set_error_listener(parser, ErrorListenerConverter())

    return parser


def parse_as_file(src_code: str) -> AtopileParser.File_inputContext:
    """
    Helper function to parse source code as a file input, returning a tree.
    """
    parser = parser_from_src_code(src_code)
    return parser.file_input()
