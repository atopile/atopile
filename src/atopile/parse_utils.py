"""
Utils related to handling the parse tree
"""
from pathlib import Path

from antlr4 import InputStream, ParserRuleContext, Token


def get_src_info_from_token(token: Token) -> tuple[str, int, int]:
    """Get the source path, line, and column from a context"""
    input_stream: InputStream = token.getInputStream()
    return input_stream.name, token.line, token.column


def get_src_info_from_ctx(ctx: ParserRuleContext) -> tuple[str | Path, int, int, int]:
    """Get the source path, line, and column from a context"""
    token: Token = ctx.start
    _, stop_line, stop_char = get_src_info_from_token(ctx.stop)
    return *get_src_info_from_token(token), stop_line, stop_char
