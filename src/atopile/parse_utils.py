"""
Utils related to handling the parse tree
"""
from antlr4 import InputStream, Token, ParserRuleContext


def get_src_info_from_token(token: Token) -> tuple[str, int, int]:
    """Get the source path, line, and column from a context"""
    input_stream: InputStream = token.getInputStream()
    return input_stream.name, token.line, token.column


def get_src_info_from_ctx(ctx: ParserRuleContext) -> tuple[str, int, int]:
    """Get the source path, line, and column from a context"""
    token: Token = ctx.start
    return get_src_info_from_token(token)
