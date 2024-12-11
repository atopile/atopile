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


def reconstruct(
    ctx: ParserRuleContext,
    mark: ParserRuleContext | None = None,
    expand_before: int | None = None,
    expand_after: int | None = None,
) -> str:
    """
    Reconstruct the source code from a parse tree

    Args:
        ctx: The parse tree to reconstruct
        mark: The context to mark with carets underneath
        expand_before: The number of lines to expand before the mark.
            0 -> To the start of the current line
        expand_after: The number of lines to expand after the mark.
            0 -> To the end of the current line
    """
    from atopile.parser.AtoLexer import AtoLexer
    from atopile.parser.AtoParser import AtoParser

    assert isinstance(ctx.parser, AtoParser)
    input_stream: CommonTokenStream = ctx.parser.getInputStream()

    newlines_before = []
    newlines_after = []
    found_start = False
    found_stop = False
    rewriter = TokenStreamRewriter(input_stream)
    for token in input_stream.tokens:
        assert isinstance(token, Token)
        if token is ctx.start:
            found_start = True
        if token is ctx.stop:
            found_stop = True

        if token.type in {AtoLexer.INDENT, AtoLexer.DEDENT}:
            rewriter.deleteToken(token)

        elif token.type == AtoLexer.NEWLINE:
            if not found_start:
                newlines_before.append(token)
            if found_stop:
                newlines_after.append(token)

            rewriter.replaceSingleToken(token, "\n")

    # Figure out where to start and stop
    if expand_before is not None:
        try:
            start_after_token = newlines_before[-expand_before - 1]
        except IndexError:
            start_token = input_stream.tokens[0]
        else:
            try:
                # Take the token after the indicated newline
                start_token = input_stream.tokens[start_after_token.tokenIndex + 1]
            except IndexError:
                # If nothing before, start at the first token
                start_token = input_stream.tokens[0]

    else:
        start_token = ctx.start

    if expand_after is not None:
        try:
            start_before_token = newlines_after[expand_after]
        except IndexError:
            # Expand to end
            stop_token = input_stream.tokens[-1]
        else:
            try:
                # Take the token after the indicated newline
                stop_token = input_stream.tokens[start_before_token.tokenIndex - 1]
            except IndexError:
                # If nothing before, start at the first token
                stop_token = input_stream.tokens[0]

    else:
        stop_token = ctx.stop

    # Generate marked code
    if mark is None:
        return rewriter.getText(
            TokenStreamRewriter.DEFAULT_PROGRAM_NAME,
            start_token.tokenIndex,
            stop_token.tokenIndex,
        )

    else:
        # Get the text up to the mark token
        before_marked: str = rewriter.getText(
            TokenStreamRewriter.DEFAULT_PROGRAM_NAME,
            start_token.tokenIndex,
            mark.start.tokenIndex - 1,
        )
        after_marked: str = rewriter.getText(
            TokenStreamRewriter.DEFAULT_PROGRAM_NAME,
            mark.start.tokenIndex,
            stop_token.tokenIndex,
        )

        # Count characters to align the marker
        last_newline = before_marked.rfind("\n")
        if last_newline < 0:
            marker_offset = len(before_marked)
        else:
            marker_offset = len(before_marked) - last_newline - 1

        # Insert the marker on the next line
        leftover_line, *remaining_content = after_marked.split("\n", 1)

        return "\n".join(
            [
                before_marked + leftover_line,
                " " * marker_offset
                + "^" * (mark.stop.tokenIndex - mark.start.tokenIndex + 1),
                *remaining_content,
            ]
        )
