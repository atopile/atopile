"""
The objective here is a make something that
translates additional useful syntax to
vanilla python for interpretation.
"""

# %%
from antlr4 import InputStream, CommonTokenStream, ParserRuleContext, Token
from PythonLexer import PythonLexer
from PythonParser import PythonParser
from PythonParserVisitor import PythonParserVisitor
from antlr4.TokenStreamRewriter import TokenStreamRewriter


class ModifyCodeVisitor(PythonParserVisitor):
    def __init__(self, tokens: CommonTokenStream):
        self.tokens = tokens
        self.rewriter = TokenStreamRewriter(tokens)

    def _rw(self, ctx: ParserRuleContext) -> str:
        return self.rewriter.getText(
            program_name=TokenStreamRewriter.DEFAULT_PROGRAM_NAME,
            start=ctx.start.tokenIndex,
            stop=ctx.stop.tokenIndex,
        )

    def visitConnect_stmt(self, ctx: PythonParser.Connect_stmtContext):
        self.visitChildren(ctx)

        self.rewriter.replaceRangeTokens(
            ctx.start,
            ctx.stop,
            f"__connect__({', '.join((self._rw(e) for e in ctx.expression()))})",
        )

    def visitTolerance(self, ctx: PythonParser.ToleranceContext):
        self.visitChildren(ctx)

        if ctx.tolerance():
            if ctx.TO():
                self.rewriter.replaceRangeTokens(
                    ctx.start,
                    ctx.stop,
                    f"__to__({self._rw(ctx.tolerance())}, {self._rw(ctx.factor())})",
                )
            elif ctx.PLUS_OR_MINUS() or ctx.PLUS_OR_MINU2():
                self.rewriter.replaceRangeTokens(
                    ctx.start,
                    ctx.stop,
                    f"__tolerance__({self._rw(ctx.tolerance())}, {self._rw(ctx.factor())})",
                )
            else:
                raise NotImplementedError

    def visitDimensioned_number(self, ctx: PythonParser.Dimensioned_numberContext):
        self.visitChildren(
            ctx
        )  # There's no need in this case, just intentionally blindly following the pattern

        unit = (ctx.NAME() or ctx.STRING()).getText().strip("\"'")
        self.rewriter.replaceRangeTokens(
            ctx.start, ctx.stop, f'__dimension__({ctx.NUMBER().getText()}, "{unit}")'
        )


def parse_code(code):
    input_stream = InputStream(code)
    lexer = PythonLexer(input_stream)
    stream = CommonTokenStream(lexer)
    parser = PythonParser(stream)
    tree = parser.file_input()
    return tree, stream


def modify_code(tree, tokens):
    visitor = ModifyCodeVisitor(tokens)
    visitor.visit(tree)
    # Cleanup the in/dedents
    # FIXME: I'm sure there must be a better way to do this
    for token in tokens.tokens:
        assert isinstance(token, Token)
        if token.type in {PythonLexer.INDENT, PythonLexer.DEDENT}:
            visitor.rewriter.deleteToken(token)
    return visitor.rewriter.getDefaultText()


source_code = """
class Demo:
    a = 10 +/- 20mV
    b = 23.5 +/- 0.5

def regular_func():
    print("Hello, world!")
"""

parse_tree, token_stream = parse_code(source_code)
modified_code = modify_code(parse_tree, token_stream)
print(modified_code)


# %%
def connect(*args):
    raise NotImplementedError


__builtins__.__connect__ = connect
