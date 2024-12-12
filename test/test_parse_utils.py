from pathlib import Path

import pytest

import atopile
import atopile.parse
import atopile.parse_utils


def _parser(src: str):
    input = atopile.parse.InputStream(src)
    input.name = "test"
    return atopile.parse.make_parser(input)


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


repo_root = Path.cwd()
while not (repo_root / "pyproject.toml").exists():
    repo_root = repo_root.parent


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
    assert atopile.parse_utils.reconstruct(file_ast) == example.read_text()


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
