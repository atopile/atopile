"""
Utils related to handling the parse tree
"""

from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Generator

import pygments.lexer
from antlr4 import CommonTokenStream, InputStream, ParserRuleContext, Token
from antlr4.TokenStreamRewriter import TokenStreamRewriter
from pygments import token as pygments_token

if TYPE_CHECKING:
    from atopile.compiler.parser.AtoLexer import AtoLexer as AtoLexerType

# Lazy-loaded AtoLexer to avoid import issues during exception handling
_AtoLexer: "type[AtoLexerType] | None" = None


def _get_ato_lexer() -> "type[AtoLexerType]":
    """Get the AtoLexer class, importing it lazily on first use."""
    global _AtoLexer
    if _AtoLexer is None:
        from atopile.compiler.parser.AtoLexer import AtoLexer

        _AtoLexer = AtoLexer
    return _AtoLexer


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
        if stream[i].type == _get_ato_lexer().NEWLINE:
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
    _drop_tokens: set[int] | None = None

    @classmethod
    def _get_drop_tokens(cls) -> set[int]:
        if cls._drop_tokens is None:
            lexer = _get_ato_lexer()
            cls._drop_tokens = {lexer.INDENT, lexer.DEDENT}
        return cls._drop_tokens

    def iter_tokens_and_text(
        self, program_name, start: int | None = None, stop: int | None = None
    ) -> Generator[tuple[Token | None, str], None, None]:
        for token, text in super().iter_tokens_and_text(program_name, start, stop):
            if token and token.type in self._get_drop_tokens():
                continue
            elif token and token.type == _get_ato_lexer().NEWLINE:
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
    _token_type_map: dict[int, "pygments_token._TokenType"] | None = None

    @classmethod
    def _get_token_type_map(cls) -> dict[int, "pygments_token._TokenType"]:
        if cls._token_type_map is None:
            lexer = _get_ato_lexer()
            cls._token_type_map = {
                lexer.INDENT: pygments_token.Token,
                lexer.DEDENT: pygments_token.Token,
                lexer.STRING: pygments_token.String,
                lexer.NUMBER: pygments_token.Number,
                lexer.INTEGER: pygments_token.Number,
                lexer.COMPONENT: pygments_token.Keyword,
                lexer.MODULE: pygments_token.Keyword,
                lexer.INTERFACE: pygments_token.Keyword,
                lexer.PIN: pygments_token.Keyword,
                lexer.SIGNAL: pygments_token.Keyword,
                lexer.NEW: pygments_token.Keyword,
                lexer.FROM: pygments_token.Keyword,
                lexer.IMPORT: pygments_token.Keyword,
                lexer.ASSERT: pygments_token.Keyword,
                lexer.TO: pygments_token.Keyword,
                lexer.TRUE: pygments_token.Name,
                lexer.FALSE: pygments_token.Name,
                lexer.WITHIN: pygments_token.Name,
                lexer.PASS: pygments_token.Keyword,
                lexer.NAME: pygments_token.Name,
                lexer.STRING_LITERAL: pygments_token.String,
                lexer.BYTES_LITERAL: pygments_token.String,
                lexer.DECIMAL_INTEGER: pygments_token.Number,
                lexer.OCT_INTEGER: pygments_token.Number,
                lexer.HEX_INTEGER: pygments_token.Number,
                lexer.BIN_INTEGER: pygments_token.Number,
                lexer.FLOAT_NUMBER: pygments_token.Number,
                lexer.IMAG_NUMBER: pygments_token.Number,
                lexer.PLUS_OR_MINUS: pygments_token.Operator,
                lexer.PLUS_SLASH_MINUS: pygments_token.Operator,
                lexer.PLUS_MINUS_SIGN: pygments_token.Operator,
                lexer.PERCENT: pygments_token.Operator,
                lexer.DOT: pygments_token.Token,
                lexer.ELLIPSIS: pygments_token.Token,
                lexer.STAR: pygments_token.Token,
                lexer.OPEN_PAREN: pygments_token.Token,
                lexer.CLOSE_PAREN: pygments_token.Token,
                lexer.COMMA: pygments_token.Token,
                lexer.COLON: pygments_token.Token,
                lexer.SEMI_COLON: pygments_token.Token,
                lexer.POWER: pygments_token.Token,
                lexer.ASSIGN: pygments_token.Operator,
                lexer.OPEN_BRACK: pygments_token.Token,
                lexer.CLOSE_BRACK: pygments_token.Token,
                lexer.OR_OP: pygments_token.Token,
                lexer.XOR: pygments_token.Token,
                lexer.AND_OP: pygments_token.Token,
                lexer.LEFT_SHIFT: pygments_token.Token,
                lexer.RIGHT_SHIFT: pygments_token.Token,
                lexer.PLUS: pygments_token.Token,
                lexer.MINUS: pygments_token.Token,
                lexer.DIV: pygments_token.Token,
                lexer.IDIV: pygments_token.Token,
                lexer.SPERM: pygments_token.Token,
                lexer.WIRE: pygments_token.Token,
                lexer.OPEN_BRACE: pygments_token.Token,
                lexer.CLOSE_BRACE: pygments_token.Token,
                lexer.LESS_THAN: pygments_token.Operator,
                lexer.GREATER_THAN: pygments_token.Operator,
                lexer.EQUALS: pygments_token.Operator,
                lexer.GT_EQ: pygments_token.Operator,
                lexer.LT_EQ: pygments_token.Operator,
                lexer.NOT_EQ_1: pygments_token.Operator,
                lexer.NOT_EQ_2: pygments_token.Operator,
                lexer.AT: pygments_token.Token,
                lexer.ARROW: pygments_token.Token,
                lexer.NEWLINE: pygments_token.Whitespace,
                lexer.COMMENT: pygments_token.Comment,
                lexer.WS: pygments_token.Whitespace,
                lexer.EXPLICIT_LINE_JOINING: pygments_token.Token,
                lexer.ERRORTOKEN: pygments_token.Error,
                lexer.FOR: pygments_token.Keyword,
                lexer.IN: pygments_token.Keyword,
            }
        return cls._token_type_map

    # Keep TOKEN_TYPE_MAP as a property for backward compatibility
    @property
    def TOKEN_TYPE_MAP(self) -> dict[int, "pygments_token._TokenType"]:
        return self._get_token_type_map()

    name = "atopile"

    aliases = ["ato"]

    filenames = ["*.ato"]

    def get_tokens_unprocessed(self, text: str):
        text_stream = InputStream(text)
        lexer = _get_ato_lexer()(text_stream)
        token_stream = CommonTokenStream(lexer)
        token_stream.fill()
        rewriter = AtoRewriter(token_stream)

        for token, text in rewriter.iter_tokens_and_text(
            TokenStreamRewriter.DEFAULT_PROGRAM_NAME
        ):
            if token is not None:
                yield (
                    token.start,
                    PygmentsLexer._get_token_type_map().get(
                        token.type, pygments_token.Token
                    ),  # type: ignore  # obviously random other shit is why I'm using .get
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
                PygmentsLexer._get_token_type_map().get(
                    token.type, pygments_token.Token
                ),  # type: ignore  # obviously random other shit is why I'm using .get
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
            ctx.parser.getInputStream(),  # type: ignore[reportOptionalMemberAccess]
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
