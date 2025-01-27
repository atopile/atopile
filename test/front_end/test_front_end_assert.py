from antlr4 import InputStream

from atopile.front_end import Bob
from atopile.parse import make_parser
from atopile.parser.AtoParser import AtoParser
from faebryk.libs.library import L


def _parse(src: str) -> AtoParser:
    input = InputStream(src)
    input.name = "test"
    return make_parser(input)


def test_assert_is(bob: Bob):
    container = L.Module()
    with bob._node_stack.enter(container):
        bob.visitDeclaration_stmt(_parse("a: dimensionless").declaration_stmt())
        bob.visitAssert_stmt(_parse("assert a is 2").assert_stmt())

    # TODO: check the constructed graph
