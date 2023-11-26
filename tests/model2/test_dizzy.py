from unittest.mock import MagicMock

import pytest

from atopile.dev.parse import parse_as_file, parser_from_src_code
from atopile.model2 import errors
from atopile.model2.builder1 import Dizzy
from atopile.model2.datamodel import (
    COMPONENT,
    INTERFACE,
    MODULE,
    PIN,
    SIGNAL,
    Import,
    Link,
    Object,
    Replace,
)

# =========================
# test individual functions
# =========================

@pytest.fixture
def dizzy():
    return Dizzy(errors.ErrorHandler(error_mode=errors.ErrorHandlerMode.RAISE_ALL))


# test Totally_an_integer
@pytest.mark.parametrize(
    "input", ["1.1", "hello", "False", "None", "True", "true", "false"]
)
def test_Totally_an_integer_errors(input, dizzy: Dizzy):
    mock_ctx = MagicMock()
    getText = MagicMock()
    getText.return_value = input
    mock_ctx.getText = getText

    with pytest.raises(errors.AtoTypeError):
        dizzy.visitTotally_an_integer(mock_ctx)


@pytest.mark.parametrize(
    ("input", "output"),
    [
        ("0", 0),
        ("1", 1),
        ("5", 5),
    ],
)
def test_Totally_an_integer_passes(input, output, dizzy: Dizzy):
    mock_ctx = MagicMock()
    getText = MagicMock()
    getText.return_value = input
    mock_ctx.getText = getText

    assert output == dizzy.visitTotally_an_integer(mock_ctx)


# test visitName
@pytest.mark.parametrize(
    ("input", "output"), [("0", 0), ("1", 1), ("5", 5), ("hello", "hello")]
)
def test_visitName(input, output, dizzy: Dizzy):
    mock_ctx = MagicMock()
    getText = MagicMock()
    getText.return_value = input
    mock_ctx.getText = getText

    assert output == dizzy.visitName(mock_ctx)


# TODO: check for a..b error at model 1 level
def test_visitAttr(dizzy: Dizzy):
    parser = parser_from_src_code("a.b.c")
    ctx = parser.attr()

    assert ("a", "b", "c") == dizzy.visitAttr(ctx)


@pytest.mark.parametrize(
    ("input", "output"),
    [
        ("a", ("a",)),
        ("a.b", ("a", "b")),
        ("a.b.c", ("a", "b", "c")),
    ],
)
def test_visitName_or_attr(input, output, dizzy: Dizzy):
    parser = parser_from_src_code(input)
    ctx = parser.name_or_attr()

    assert output == dizzy.visitName_or_attr(ctx)


@pytest.mark.parametrize(
    ("input", "output"),
    [
        ("0", ("0",)),
        ("1", ("1",)),
        ("3", ("3",)),
    ],
)
def test_visit_ref_helper_totally_an_integer(input, output, dizzy: Dizzy):
    parser = parser_from_src_code(input)
    ctx = parser.totally_an_integer()

    assert output == dizzy.visit_ref_helper(ctx)


@pytest.mark.parametrize(
    ("input", "output"),
    [
        ("a", ("a",)),
        ("a.b", ("a", "b")),
        ("a.b.c", ("a", "b", "c")),
    ],
)
def test_visit_ref_helper_name_or_attr(input, output, dizzy: Dizzy):
    parser = parser_from_src_code(input)
    ctx = parser.name_or_attr()

    assert output == dizzy.visit_ref_helper(ctx)


def test_visit_ref_helper_name(dizzy: Dizzy):
    parser = parser_from_src_code("sparkles")
    ctx = parser.name()

    assert ("sparkles",) == dizzy.visit_ref_helper(ctx)


# =============
# test compiler
# =============


def test_interface(dizzy: Dizzy):
    tree = parse_as_file(
        """
        interface interface1:
            signal signal_a
            signal signal_b
        """
    )
    results = dizzy.visitFile_input(tree)
    results.src_ctx = None
    assert results.supers_refs == MODULE
    assert len(results.locals_) == 1
    assert results.locals_[0].ref == ("interface1",)
    interface: Object = results.locals_[0].value
    assert interface.supers_refs == INTERFACE
    assert len(interface.locals_) == 2
    assert interface.locals_[0].ref == ("signal_a",)
    assert interface.locals_[0].value.supers_refs == SIGNAL
    assert interface.locals_[1].ref == ("signal_b",)
    assert interface.locals_[1].value.supers_refs == SIGNAL


def test_visitSignaldef_stmt(dizzy: Dizzy):
    parser = parser_from_src_code("signal signal_a")
    ctx = parser.signaldef_stmt()

    ret = dizzy.visitSignaldef_stmt(ctx)
    assert isinstance(ret, tuple)

    assert len(ret) == 1
    assert ret[0].ref == ("signal_a",)

    assert isinstance(ret[0].value, Object)
    assert ret[0].value.supers_refs == SIGNAL


def test_visitPindef_stmt(dizzy: Dizzy):
    parser = parser_from_src_code("pin pin_a")
    ctx = parser.pindef_stmt()

    ret = dizzy.visitPindef_stmt(ctx)
    assert isinstance(ret, tuple)
    assert len(ret) == 1
    assert ret[0].ref == ("pin_a",)
    assert isinstance(ret[0].value, Object)
    assert ret[0].value.supers_refs == PIN


# Connect statement return a tuple as there might be signal or pin instantiation within it
def test_visitConnect_stmt_simple(dizzy: Dizzy):
    parser = parser_from_src_code("pin_a ~ pin_b")
    ctx = parser.connect_stmt()

    ret = dizzy.visitConnect_stmt(ctx)
    assert len(ret[0]) == 2
    link = ret[0][1]
    assert link.source_ref == ("pin_a",)
    assert link.target_ref == ("pin_b",)


def test_visitRetype_stmt(dizzy: Dizzy):
    parser = parser_from_src_code("a -> b")
    ctx = parser.retype_stmt()

    ret = dizzy.visitRetype_stmt(ctx)
    ret[0].value.src_ctx = None
    assert len(ret) == 1
    assert ret[0] == (None, Replace(original_ref=("a",), replacement_ref=("b",)))


def test_visitConnect_stmt_instance(dizzy: Dizzy):
    parser = parser_from_src_code("pin pin_a ~ signal sig_b")
    ctx = parser.connect_stmt()

    ret = dizzy.visitConnect_stmt(ctx)

    assert isinstance(ret, tuple)
    assert len(ret) == 3

    assert ret[0].ref is None
    assert isinstance(ret[0].value, Link)
    assert ret[0].value.source_ref == ("pin_a",)
    assert ret[0].value.target_ref == ("sig_b",)

    assert ret[1].ref == ("pin_a",)
    assert isinstance(ret[1].value, Object)
    assert ret[1].value.supers_refs == PIN

    assert ret[2].ref == ("sig_b",)
    assert isinstance(ret[2].value, Object)
    assert ret[2].value.supers_refs == SIGNAL


def test_visitImport_stmt(dizzy: Dizzy):
    parser = parser_from_src_code("import Module1 from 'test_import.ato'")
    ctx = parser.import_stmt()

    ret = dizzy.visitImport_stmt(ctx)
    ret[0].value.src_ctx = None
    assert len(ret) == 1
    assert ret[0] == (("Module1",), Import(what_ref=("Module1",), from_name="test_import.ato"))


def test_visitBlockdef(dizzy: Dizzy):
    parser = parser_from_src_code(
        """
        component comp1 from comp2:
            signal signal_a
        """.strip()
    )
    ctx = parser.blockdef()

    results = dizzy.visitBlockdef(ctx)

    assert results.ref == ("comp1",)

    comp1: Object = results.value
    assert isinstance(comp1, Object)
    assert comp1.supers_refs == (("comp2",),)
    assert len(comp1.locals_) == 1

    assert comp1.locals_[0].ref == ("signal_a",)
    comp2: Object = comp1.locals_[0].value
    assert isinstance(comp2, Object)
    assert comp2.supers_refs == SIGNAL


def test_visitAssign_stmt_value(dizzy: Dizzy):
    parser = parser_from_src_code("foo.bar = 35")
    ctx = parser.assign_stmt()

    results = dizzy.visitAssign_stmt(ctx)
    assert len(results) == 1
    assert results[0] == (("foo", "bar"), 35)


def test_visitAssign_stmt_string(dizzy: Dizzy):
    parser = parser_from_src_code('foo.bar = "baz"')
    ctx = parser.assign_stmt()

    results = dizzy.visitAssign_stmt(ctx)
    assert len(results) == 1
    assert results[0] == (("foo", "bar"), "baz")


def test_visitNew_stmt(dizzy: Dizzy):
    parser = parser_from_src_code("new Bar")
    ctx = parser.new_stmt()

    results = dizzy.visitNew_stmt(ctx)
    assert isinstance(results, Object)
    assert results.supers_refs == (("Bar",),)
    assert results.locals_ == ()


def test_visitModule1LayerDeep(dizzy: Dizzy):
    tree = parse_as_file(
        """
        component comp1:
            signal signal_a
            signal signal_b
            signal_a ~ signal_b
        """
    )
    results = dizzy.visitFile_input(tree)
    assert isinstance(results, Object)
    assert results.supers_refs == MODULE
    assert len(results.locals_) == 1
    assert results.locals_[0].ref == ("comp1",)
    comp1: Object = results.locals_[0].value
    assert comp1.supers_refs == COMPONENT
    assert len(comp1.locals_) == 3
    assert comp1.locals_[0].ref == ("signal_a",)
    assert isinstance(comp1.locals_[0].value, Object)
    assert comp1.locals_[0].value.supers_refs == SIGNAL
    assert comp1.locals_[1].ref == ("signal_b",)
    assert isinstance(comp1.locals_[1].value, Object)
    assert comp1.locals_[1].value.supers_refs == SIGNAL
    assert comp1.locals_[2].ref is None
    assert isinstance(comp1.locals_[2].value, Link)
    assert comp1.locals_[2].value.source_ref == ("signal_a",)
    assert comp1.locals_[2].value.target_ref == ("signal_b",)


def test_visitModule_pin_to_signal(dizzy: Dizzy):
    tree = parse_as_file(
        """
        component comp1:
            signal signal_a ~ pin p1
        """
    )
    results = dizzy.visitFile_input(tree)
    assert isinstance(results, Object)
    assert results.supers_refs == MODULE
    assert len(results.locals_) == 1

    assert results.locals_[0].ref == ("comp1",)
    comp1: Object = results.locals_[0].value
    assert comp1.supers_refs == COMPONENT
    assert len(comp1.locals_) == 3

    assert comp1.locals_[0].ref is None
    link = comp1.locals_[0].value
    assert isinstance(link, Link)
    assert link.source_ref == ("signal_a",)
    assert link.target_ref == ("p1",)

    assert comp1.locals_[1].ref == ("signal_a",)
    assert isinstance(comp1.locals_[1].value, Object)
    assert comp1.locals_[1].value.supers_refs == SIGNAL

    assert comp1.locals_[2].ref == ("p1",)
    assert isinstance(comp1.locals_[2].value, Object)
    assert comp1.locals_[2].value.supers_refs == PIN
