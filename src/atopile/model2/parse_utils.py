"""
Utils related to handling the parse tree
"""
from antlr4 import InputStream, Token


def get_src_info_from_ctx(ctx) -> tuple[str, str, str]:
    """Get the source path, line, and column from a context"""
    token: Token = ctx.start
    input_stream: InputStream = ctx.start.source[1]
    return input_stream.name, token.line, token.column
