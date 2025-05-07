from pathlib import Path

import pytest
from pygments import token as pygments_token

import atopile
import atopile.parse
import atopile.parse_utils
from faebryk.libs.util import repo_root as _repo_root


def _parser(src: str):
    input = atopile.parse.InputStream(src)
    input.name = "test"
    parser, _ = atopile.parse.make_parser(input)
    return parser


@pytest.mark.parametrize(
    "txt",
    [
        "a = 1",
        "assert 1 within 2",
        "b = 1kV +/- 10% + (2V - 1V)",
    ],
)
def test_reconstructor_simple_stmt(txt: str):
    """Ensure we can faithfully re-construct the source code from a parse tree"""
    assert atopile.parse_utils.reconstruct(_parser(txt).simple_stmt()) == txt


repo_root = _repo_root()
EXAMPLES_DIR = repo_root / "examples"


@pytest.mark.slow
@pytest.mark.parametrize(
    "example",
    [p for p in EXAMPLES_DIR.glob("*.ato") if p.is_file()],
    ids=lambda p: p.stem,
)
def test_example_reconstruction(example: Path):
    assert example.exists()
    file_ast = atopile.parse.parse_file(example)
    assert atopile.parse_utils.reconstruct(file_ast) == example.read_text(
        encoding="utf-8"
    )


def test_partial_reconstruction():
    code = "a=1;b=2"
    file_ast = atopile.parse.parse_text_as_file(code)
    assert (
        atopile.parse_utils.reconstruct(
            file_ast.stmt()[0].simple_stmts().simple_stmt()[1]
        )
        == "b=2"
    )


@pytest.fixture
def abcde():
    code = {
        "a": "a=1",
        "b": "b=2",
        "c": "c=3",
        "d": "d=4",
        "e": "e=5",
    }
    src = "a=1;b=2\nc=3;d=4\ne=5"
    file_ast = atopile.parse.parse_text_as_file(src)
    stmts = {
        "a": file_ast.stmt()[0].simple_stmts().simple_stmt()[0],
        "b": file_ast.stmt()[0].simple_stmts().simple_stmt()[1],
        "c": file_ast.stmt()[1].simple_stmts().simple_stmt()[0],
        "d": file_ast.stmt()[1].simple_stmts().simple_stmt()[1],
        "e": file_ast.stmt()[2].simple_stmts().simple_stmt()[0],
    }
    return file_ast, stmts, code


def test_reconstruct_expand(abcde):
    _, stmts, _ = abcde
    assert atopile.parse_utils.reconstruct(stmts["c"]) == "c=3"
    assert atopile.parse_utils.reconstruct(stmts["c"], expand_before=0) == "c=3"
    assert (
        atopile.parse_utils.reconstruct(stmts["c"], expand_before=1) == "a=1;b=2\nc=3"
    )
    assert atopile.parse_utils.reconstruct(stmts["c"], expand_after=0) == "c=3;d=4"
    assert atopile.parse_utils.reconstruct(stmts["c"], expand_after=1) == "c=3;d=4\ne=5"
    assert atopile.parse_utils.reconstruct(stmts["d"]) == "d=4"
    assert atopile.parse_utils.reconstruct(stmts["d"], expand_after=0) == "d=4"
    assert atopile.parse_utils.reconstruct(stmts["d"], expand_before=0) == "c=3;d=4"


def test_pygments_lexer():
    text = """module Test:
    a = 1
"""
    lexer = atopile.parse_utils.PygmentsLexer()
    tok_gen = lexer.get_tokens_unprocessed(text)
    assert list(filter(lambda t: t[1] != pygments_token.Whitespace, tok_gen)) == [
        (0, pygments_token.Keyword, "module"),
        (7, pygments_token.Name, "Test"),
        (11, pygments_token.Token, ":"),
        (17, pygments_token.Name, "a"),
        (19, pygments_token.Operator, "="),
        (21, pygments_token.Number, "1"),
    ]
