"""
Utils related to handling the parse tree
"""
from pathlib import Path
from typing import Any, Optional

from antlr4 import (
    InputStream,
    Lexer,
    ParserRuleContext,
    ParseTreeVisitor,
    Token,
)


def get_src_info_from_token(token: Token) -> tuple[str, int, int]:
    """Get the source path, line, and column from a context"""
    input_stream: InputStream = token.getInputStream()
    return input_stream.name, token.line, token.column


def get_src_info_from_ctx(ctx: ParserRuleContext) -> tuple[str | Path, int, int, int, int]:
    """Get the source path, line, and column from a context"""
    token: Token = ctx.start
    _, stop_line, stop_char = get_src_info_from_token(ctx.stop)
    return *get_src_info_from_token(token), stop_line, stop_char


def format_src_info(ctx: ParserRuleContext) -> str:
    """Format the source path, line, and column"""
    src, start_line, start_col, _, _ = get_src_info_from_ctx(ctx)
    return f"{src}:{start_line}:{start_col}"


# FIXME: I hate this pattern
# It should instead at least return a list of tokens
# for processing in a regular for loop
class _Reconstructor(ParseTreeVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.txt = ""
        self.last_line = None
        self.last_col = None

    def visitTerminal(self, node) -> str:
        symbol: Token = node.getSymbol()

        if self.last_line is None:
            self.last_line = symbol.line
            self.last_col = symbol.start

        if symbol.line > self.last_line:
            self.txt += "\n" * (symbol.line - self.last_line)
            self.last_col = 0

        self.txt += " " * (symbol.start - self.last_col - 1)

        self.last_line = symbol.line
        self.last_col = symbol.stop

        self.txt += node.getText()
        return super().visitTerminal(node)


def reconstruct(ctx: ParserRuleContext) -> str:
    """Reconstruct the source code from a parse tree"""
    reco = _Reconstructor()
    reco.visit(ctx)
    return reco.txt


def get_comment_from_token(token: Token) -> Optional[str]:
    """Return the comment from a token's start line."""
    lexer: Optional[Lexer] = token.getTokenSource()
    if not lexer or not hasattr(lexer, "comments"):
        return None

    comments: dict[tuple[Any, int], str] = lexer.comments
    line: int = token.line

    if input_stream := token.getInputStream():
        source_name = input_stream.name
    else:
        return None

    return comments.get((source_name, line))
