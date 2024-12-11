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


def test_marked_reconstruction():
    code = "a=1;b=2\nc=3;d=4\ne=5"
    file_ast = atopile.parse.parse_text_as_file(code)
    second_stmt = file_ast.stmt()[1].simple_stmts().simple_stmt()[1]

    reconstructed = atopile.parse_utils.reconstruct(
        file_ast,
        mark=second_stmt,
    )

    assert reconstructed == "a=1;b=2\nc=3;d=4\n    ^^^\ne=5\n"
