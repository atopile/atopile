import logging
from textwrap import dedent

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

from atopile.model2.errors import AtoSyntaxError
from atopile.model2.parse import ParserRuleContext
from atopile.parser.AtopileLexer import AtopileLexer
from atopile.parser.AtopileParser import AtopileParser

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class ParserErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        raise AtoSyntaxError(f"Syntax error: '{msg}'", line, column)


def make_parser(src_code: str) -> AtopileParser:
    input = InputStream(dedent(src_code))

    lexer = AtopileLexer(input)
    stream = CommonTokenStream(lexer)
    parser = AtopileParser(stream)

    error_listener = ParserErrorListener()
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)

    return parser


def parse_as_file(src_code: str) -> ParserRuleContext:
    parser = make_parser(src_code)
    return parser.file_input()
