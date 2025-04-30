"""
Utils related to handling the parse tree
"""

from io import StringIO
from pathlib import Path
from typing import Generator

import pygments.lexer
from antlr4 import CommonTokenStream, InputStream, ParserRuleContext, Token
from antlr4.TokenStreamRewriter import TokenStreamRewriter
from pygments import token as pygments_token

from atopile.parser.AtoLexer import AtoLexer


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


def expand(
    stream: list[Token], beginning: int, step: int, count: int | None = None
) -> int:
    """
    Expand the stream by the given amount in the given direction
    """
    if count is None:
        return beginning

    i = beginning
    newlines_to_find = count
    while 0 <= i < len(stream):
        if stream[i].type == AtoLexer.NEWLINE:
            if newlines_to_find == 0:
                return i - step
            newlines_to_find -= 1
        i += step

    return min(max(i, 0), len(stream) - 1)


class IterableRewriter(TokenStreamRewriter):
    def iter_tokens_and_text(
        self, program_name, start: int | None = None, stop: int | None = None
    ) -> Generator[tuple[Token | None, str], None, None]:
        """
        :return: the text in tokens[start, stop](closed interval)
        """
        rewrites = self.programs.get(program_name)

        # ensure start/end are in range
        if stop is None or stop > len(self.tokens.tokens) - 1:
            stop = len(self.tokens.tokens) - 1
        if start is None or start < 0:
            start = 0

        indexToOp = self._reduceToSingleOperationPerIndex(rewrites)
        i = start
        while all((i <= stop, i < len(self.tokens.tokens))):
            op = indexToOp.pop(i, None)
            token = self.tokens.get(i)
            if op is None:
                if token.type != Token.EOF:
                    yield token, token.text
                i += 1
            else:
                buf = StringIO()
                i = op.execute(buf)
                yield token, buf.getvalue()

        if stop == len(self.tokens.tokens) - 1:
            for op in indexToOp.values():
                if op.index >= len(self.tokens.tokens) - 1:
                    yield None, op.text


class AtoRewriter(IterableRewriter):
    DROP_TOKENS = {AtoLexer.INDENT, AtoLexer.DEDENT}

    def iter_tokens_and_text(
        self, program_name, start: int | None = None, stop: int | None = None
    ) -> Generator[tuple[Token | None, str], None, None]:
        for token, text in super().iter_tokens_and_text(program_name, start, stop):
            if token and token.type in self.DROP_TOKENS:
                continue
            elif token and token.type == AtoLexer.NEWLINE:
                # FIXME: feels like we shouldn't have this
                yield token, "\n"
            else:
                yield token, text

    def getText(self, program_name, start: int, stop: int):
        return self.get_text(program_name, start, stop)

    def get_text(self, program_name, start: int, stop: int):
        return "".join(
            text for _, text in self.iter_tokens_and_text(program_name, start, stop)
        )


class PygmentsLexer(pygments.lexer.Lexer):
    TOKEN_TYPE_MAP = {
        AtoLexer.INDENT: pygments_token.Token,
        AtoLexer.DEDENT: pygments_token.Token,
        AtoLexer.STRING: pygments_token.String,
        AtoLexer.NUMBER: pygments_token.Number,
        AtoLexer.INTEGER: pygments_token.Number,
        AtoLexer.COMPONENT: pygments_token.Keyword,
        AtoLexer.MODULE: pygments_token.Keyword,
        AtoLexer.INTERFACE: pygments_token.Keyword,
        AtoLexer.PIN: pygments_token.Keyword,
        AtoLexer.SIGNAL: pygments_token.Keyword,
        AtoLexer.NEW: pygments_token.Keyword,
        AtoLexer.FROM: pygments_token.Keyword,
        AtoLexer.IMPORT: pygments_token.Keyword,
        AtoLexer.ASSERT: pygments_token.Keyword,
        AtoLexer.TO: pygments_token.Keyword,
        AtoLexer.TRUE: pygments_token.Name,
        AtoLexer.FALSE: pygments_token.Name,
        AtoLexer.WITHIN: pygments_token.Name,
        AtoLexer.PASS: pygments_token.Keyword,
        AtoLexer.NAME: pygments_token.Name,
        AtoLexer.STRING_LITERAL: pygments_token.String,
        AtoLexer.BYTES_LITERAL: pygments_token.String,
        AtoLexer.DECIMAL_INTEGER: pygments_token.Number,
        AtoLexer.OCT_INTEGER: pygments_token.Number,
        AtoLexer.HEX_INTEGER: pygments_token.Number,
        AtoLexer.BIN_INTEGER: pygments_token.Number,
        AtoLexer.FLOAT_NUMBER: pygments_token.Number,
        AtoLexer.IMAG_NUMBER: pygments_token.Number,
        AtoLexer.PLUS_OR_MINUS: pygments_token.Operator,
        AtoLexer.PLUS_SLASH_MINUS: pygments_token.Operator,
        AtoLexer.PLUS_MINUS_SIGN: pygments_token.Operator,
        AtoLexer.PERCENT: pygments_token.Operator,
        AtoLexer.DOT: pygments_token.Token,
        AtoLexer.ELLIPSIS: pygments_token.Token,
        AtoLexer.STAR: pygments_token.Token,
        AtoLexer.OPEN_PAREN: pygments_token.Token,
        AtoLexer.CLOSE_PAREN: pygments_token.Token,
        AtoLexer.COMMA: pygments_token.Token,
        AtoLexer.COLON: pygments_token.Token,
        AtoLexer.SEMI_COLON: pygments_token.Token,
        AtoLexer.POWER: pygments_token.Token,
        AtoLexer.ASSIGN: pygments_token.Operator,
        AtoLexer.OPEN_BRACK: pygments_token.Token,
        AtoLexer.CLOSE_BRACK: pygments_token.Token,
        AtoLexer.OR_OP: pygments_token.Token,
        AtoLexer.XOR: pygments_token.Token,
        AtoLexer.AND_OP: pygments_token.Token,
        AtoLexer.LEFT_SHIFT: pygments_token.Token,
        AtoLexer.RIGHT_SHIFT: pygments_token.Token,
        AtoLexer.PLUS: pygments_token.Token,
        AtoLexer.MINUS: pygments_token.Token,
        AtoLexer.DIV: pygments_token.Token,
        AtoLexer.IDIV: pygments_token.Token,
        AtoLexer.SPERM: pygments_token.Token,
        AtoLexer.WIRE: pygments_token.Token,
        AtoLexer.OPEN_BRACE: pygments_token.Token,
        AtoLexer.CLOSE_BRACE: pygments_token.Token,
        AtoLexer.LESS_THAN: pygments_token.Operator,
        AtoLexer.GREATER_THAN: pygments_token.Operator,
        AtoLexer.EQUALS: pygments_token.Operator,
        AtoLexer.GT_EQ: pygments_token.Operator,
        AtoLexer.LT_EQ: pygments_token.Operator,
        AtoLexer.NOT_EQ_1: pygments_token.Operator,
        AtoLexer.NOT_EQ_2: pygments_token.Operator,
        AtoLexer.AT: pygments_token.Token,
        AtoLexer.ARROW: pygments_token.Token,
        AtoLexer.ADD_ASSIGN: pygments_token.Token,
        AtoLexer.SUB_ASSIGN: pygments_token.Token,
        AtoLexer.MULT_ASSIGN: pygments_token.Token,
        AtoLexer.AT_ASSIGN: pygments_token.Token,
        AtoLexer.DIV_ASSIGN: pygments_token.Token,
        AtoLexer.AND_ASSIGN: pygments_token.Token,
        AtoLexer.OR_ASSIGN: pygments_token.Token,
        AtoLexer.XOR_ASSIGN: pygments_token.Token,
        AtoLexer.LEFT_SHIFT_ASSIGN: pygments_token.Token,
        AtoLexer.RIGHT_SHIFT_ASSIGN: pygments_token.Token,
        AtoLexer.POWER_ASSIGN: pygments_token.Token,
        AtoLexer.IDIV_ASSIGN: pygments_token.Token,
        AtoLexer.NEWLINE: pygments_token.Whitespace,
        AtoLexer.COMMENT: pygments_token.Comment,
        AtoLexer.WS: pygments_token.Whitespace,
        AtoLexer.EXPLICIT_LINE_JOINING: pygments_token.Token,
        AtoLexer.ERRORTOKEN: pygments_token.Error,
        AtoLexer.FOR: pygments_token.Keyword,
        AtoLexer.IN: pygments_token.Keyword,
    }

    name = "atopile"

    aliases = ["ato"]

    filenames = ["*.ato"]

    def get_tokens_unprocessed(self, text: str):
        text_stream = InputStream(text)
        lexer = AtoLexer(text_stream)
        token_stream = CommonTokenStream(lexer)
        token_stream.fill()
        rewriter = AtoRewriter(token_stream)

        for token, text in rewriter.iter_tokens_and_text(
            TokenStreamRewriter.DEFAULT_PROGRAM_NAME
        ):
            if token is not None:
                yield (
                    token.start,
                    PygmentsLexer.TOKEN_TYPE_MAP.get(token.type, pygments_token.Token),  # type: ignore  # obviously random other shit is why I'm using .get
                    text,
                )


class PygmentsLexerReconstructor(pygments.lexer.Lexer):
    """Reconstruct source-code from a ctx, and antlr4 rewriter"""

    def __init__(
        self,
        rewriter: AtoRewriter,
        start: int,
        stop: int,
    ):
        self.rewriter = rewriter
        self.start = start
        self.stop = stop

    def get_code(self) -> str:
        return self.rewriter.getText(
            TokenStreamRewriter.DEFAULT_PROGRAM_NAME, self.start, self.stop
        )

    def get_tokens(
        self, _: str
    ) -> Generator[tuple["pygments_token._TokenType", str], None, None]:
        for token, text in self.rewriter.iter_tokens_and_text(
            TokenStreamRewriter.DEFAULT_PROGRAM_NAME, self.start, self.stop
        ):
            yield (
                PygmentsLexer.TOKEN_TYPE_MAP.get(token.type, pygments_token.Token),  # type: ignore  # obviously random other shit is why I'm using .get
                text,
            )

    @classmethod
    def from_tokens(
        cls,
        token_stream: CommonTokenStream,
        start_token: Token,
        stop_token: Token | None = None,
        expand_before: int | None = None,
        expand_after: int | None = None,
    ) -> "PygmentsLexerReconstructor":
        rewriter = AtoRewriter(token_stream)

        start_index = expand(
            token_stream.tokens, start_token.tokenIndex, -1, expand_before
        )

        if stop_token is None:
            stop_token = start_token

        stop_index = expand(token_stream.tokens, stop_token.tokenIndex, 1, expand_after)

        return PygmentsLexerReconstructor(rewriter, start_index, stop_index)

    @classmethod
    def from_ctx(
        cls,
        ctx: ParserRuleContext,
        expand_before: int | None = None,
        expand_after: int | None = None,
    ) -> "PygmentsLexerReconstructor":
        return cls.from_tokens(
            ctx.parser.getInputStream(),  # type: ignore
            ctx.start,
            ctx.stop,
            expand_before,
            expand_after,
        )

    @property
    def start_line(self) -> int:
        return self.rewriter.tokens.tokens[self.start].line


def reconstruct(
    ctx: ParserRuleContext,
    expand_before: int | None = None,
    expand_after: int | None = None,
) -> str:
    """
    Reconstruct the source code from a parse tree

    Args:
        ctx: The parse tree to reconstruct
        expand_before: The number of lines to expand before the mark.
            0 -> To the start of the current line
        expand_after: The number of lines to expand after the mark.
            0 -> To the end of the current line
    """
    return PygmentsLexerReconstructor.from_ctx(
        ctx, expand_before, expand_after
    ).get_code()
