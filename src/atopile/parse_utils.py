"""
Utils related to handling the parse tree
"""

from pathlib import Path

from antlr4 import CommonTokenStream, InputStream, ParserRuleContext, Token
from antlr4.TokenStreamRewriter import TokenStreamRewriter


def get_src_info_from_token(token: Token) -> tuple[str, int, int]:
    """Get the source path, line, and column from a context"""
    input_stream: InputStream = token.getInputStream()
    return input_stream.name, token.line, token.column


def get_src_info_from_ctx(
    ctx: ParserRuleContext,
) -> tuple[str | Path, int, int, int, int]:
    """Get the source path, line, and column from a context"""
    token: Token = ctx.start
    return (
        *get_src_info_from_token(token),
        ctx.stop.line,
        ctx.stop.column + len(ctx.stop.text),
    )


def format_src_info(ctx: ParserRuleContext) -> str:
    """Format the source path, line, and column"""
    src, start_line, start_col, _, _ = get_src_info_from_ctx(ctx)
    return f"{src}:{start_line}:{start_col}"


def reconstruct(ctx: ParserRuleContext, mark: ParserRuleContext | None = None) -> str:
    """Reconstruct the source code from a parse tree"""
    from atopile.parser.AtoLexer import AtoLexer
    from atopile.parser.AtoParser import AtoParser

    assert isinstance(ctx.parser, AtoParser)
    input_stream: CommonTokenStream = ctx.parser.getInputStream()

    rewriter = TokenStreamRewriter(input_stream)
    for token in input_stream.tokens:
        assert isinstance(token, Token)
        if token.type in {AtoLexer.INDENT, AtoLexer.DEDENT}:
            rewriter.deleteToken(token)
        elif token.type == AtoLexer.NEWLINE:
            rewriter.replaceSingleToken(token, "\n")

    if mark is None:
        return rewriter.getText(
            TokenStreamRewriter.DEFAULT_PROGRAM_NAME,
            ctx.start.tokenIndex,
            ctx.stop.tokenIndex,
        )

    else:
        # Get the text up to the mark token
        before_marked: str = rewriter.getText(
            TokenStreamRewriter.DEFAULT_PROGRAM_NAME,
            ctx.start.tokenIndex,
            mark.start.tokenIndex - 1,
        )
        after_marked: str = rewriter.getText(
            TokenStreamRewriter.DEFAULT_PROGRAM_NAME,
            mark.start.tokenIndex,
            ctx.stop.tokenIndex,
        )

        # Count characters to align the marker
        last_newline = before_marked.rfind("\n")
        if last_newline < 0:
            marker_offset = len(before_marked)
        else:
            marker_offset = len(before_marked) - last_newline - 1

        # Insert the marker on the next line
        leftover_line, *remaining_content = after_marked.split("\n", 1)

        if remaining_content and not remaining_content[0]:
            remaining_content = []

        return "\n".join(
            [
                before_marked + leftover_line,
                " " * marker_offset
                + "^" * (mark.stop.tokenIndex - mark.start.tokenIndex + 1),
                *remaining_content,
            ]
        )
