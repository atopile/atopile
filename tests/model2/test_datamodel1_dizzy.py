from atopile.dev.parse import parse_as_file, make_parser
from atopile.model2.datamodel1 import Object, Link, Import, Dizzy, Replace
from atopile.model2.datamodel1 import MODULE, COMPONENT, PIN, SIGNAL, INTERFACE
from atopile.model2 import errors
from unittest.mock import MagicMock
import pytest

# =========================
# test individual functions
# =========================

# test Totally_an_integer
@pytest.mark.parametrize(
    "input",
    [
        "1.1",
        "hello",
        "False",
        "None",
        "True",
        "true",
        "false"
    ]
)
def test_Totally_an_integer_errors(input):
    mock_ctx = MagicMock()
    getText = MagicMock()
    getText.return_value = input
    mock_ctx.getText = getText

    with pytest.raises(errors.AtoTypeError):
        dizzy = Dizzy("test.ato")
        dizzy.visitTotally_an_integer(mock_ctx)


@pytest.mark.parametrize(
    ("input", "output"),
    [
        ("0", 0),
        ("1", 1),
        ("5", 5),
    ]
)
def test_Totally_an_integer_passes(input, output):
    mock_ctx = MagicMock()
    getText = MagicMock()
    getText.return_value = input
    mock_ctx.getText = getText

    dizzy = Dizzy("test.ato")
    assert output == dizzy.visitTotally_an_integer(mock_ctx)

# test visitName
@pytest.mark.parametrize(
    ("input", "output"),
    [
        ("0", 0),
        ("1", 1),
        ("5", 5),
        ("hello", "hello")
    ]
)
def test_visitName(input, output):
    mock_ctx = MagicMock()
    getText = MagicMock()
    getText.return_value = input
    mock_ctx.getText = getText

    dizzy = Dizzy("test.ato")
    assert output == dizzy.visitName(mock_ctx)

#TODO: check for a..b error at model 1 level
def test_visitAttr():
    parser = make_parser("a.b.c")
    ctx = parser.attr()

    dizzy = Dizzy("test.ato")
    assert ("a", "b", "c") == dizzy.visitAttr(ctx)

@pytest.mark.parametrize(
    ("input", "output"),
    [
        ("a", ("a",)),
        ("a.b", ("a","b")),
        ("a.b.c", ("a","b","c")),
    ]
)
def test_visitName_or_attr(input, output):
    parser = make_parser(input)
    ctx = parser.name_or_attr()

    dizzy = Dizzy("test.ato")
    assert output == dizzy.visitName_or_attr(ctx)

@pytest.mark.parametrize(
    ("input", "output"),
    [
        ("0", (0,)),
        ("1", (1,)),
        ("3", (3,)),
    ]
)
def test_visit_ref_helper_totally_an_integer(input, output):
    parser = make_parser(input)
    ctx = parser.totally_an_integer()

    dizzy = Dizzy("test.ato")
    assert output == dizzy.visit_ref_helper(ctx)

@pytest.mark.parametrize(
    ("input", "output"),
    [
        ("a", ("a",)),
        ("a.b", ("a","b")),
        ("a.b.c", ("a","b","c")),
    ]
)
def test_visit_ref_helper_name_or_attr(input, output):
    parser = make_parser(input)
    ctx = parser.name_or_attr()

    dizzy = Dizzy("test.ato")
    assert output == dizzy.visit_ref_helper(ctx)

def test_visit_ref_helper_name():
    parser = make_parser("sparkles")
    ctx = parser.name()

    dizzy = Dizzy("test.ato")
    assert ("sparkles",) == dizzy.visit_ref_helper(ctx)

# =============
# test compiler
# =============

def test_interface():
    tree = parse_as_file(
        """
        interface interface1:
            signal signal_a
            signal signal_b
        """
    )
    dizzy = Dizzy("test.ato")
    results = dizzy.visitFile_input(tree)
    assert results == Object(supers=MODULE, locals_=(
        (('interface1',), Object(supers=INTERFACE,
        locals_= (
            (('signal_a',), Object(supers=SIGNAL)),
            (('signal_b',), Object(supers=SIGNAL))
        ))),
    ))

def test_visitSignaldef_stmt():
    parser = make_parser("signal signal_a")
    ctx = parser.signaldef_stmt()

    dizzy = Dizzy("test.ato")
    ret = dizzy.visitSignaldef_stmt(ctx)
    assert ret == ((('signal_a',), Object(supers=SIGNAL)),)


def test_visitPindef_stmt():
    parser = make_parser("pin pin_a")
    ctx = parser.pindef_stmt()

    dizzy = Dizzy("test.ato")
    ret = dizzy.visitPindef_stmt(ctx)
    assert ret == ((('pin_a',), Object(supers=PIN)),)

# Connect statement return a tuple as there might be signal or pin instantiation within it
def test_visitConnect_stmt_simple():
    parser = make_parser("pin_a ~ pin_b")
    ctx = parser.connect_stmt()

    dizzy = Dizzy("test.ato")
    ret = dizzy.visitConnect_stmt(ctx)
    assert ret == ((None, Link(source=('pin_a',), target=('pin_b',))),)

def test_visitRetype_stmt():
    parser = make_parser("a -> b")
    ctx = parser.retype_stmt()

    dizzy = Dizzy("test.ato")
    ret = dizzy.visitRetype_stmt(ctx)
    assert len(ret) == 1
    assert ret[0] == (None, Replace(original=('a',), replacement=('b',)))

def test_visitConnect_stmt_instance():
    parser = make_parser("pin pin_a ~ signal sig_b")
    ctx = parser.connect_stmt()

    dizzy = Dizzy("test.ato")
    ret = dizzy.visitConnect_stmt(ctx)
    assert ret == (
        (None,       Link(source=('pin_a',), target=('sig_b',))),
        (('pin_a',), Object(supers=PIN)),
        (('sig_b',), Object(supers=SIGNAL))
    )

def test_visitImport_stmt():
    parser = make_parser("import Module1 from 'test_import.ato'")
    ctx = parser.import_stmt()

    dizzy = Dizzy("test.ato")
    ret = dizzy.visitImport_stmt(ctx)
    assert len(ret) == 1
    assert ret[0] == (('Module1',), Import(what=('Module1',), from_='test_import.ato'))

def test_visitBlockdef():
    parser = make_parser(
        """
        component comp1 from comp2:
            signal signal_a
        """.strip()
    )
    ctx = parser.blockdef()

    dizzy = Dizzy("test.ato")
    results = dizzy.visitBlockdef(ctx)
    assert results == (
        ('comp1',),
        Object(
            supers=(('comp2',),),
            locals_=((('signal_a',), Object(supers=SIGNAL, locals_=())),)
        )
    )

def test_visitAssign_stmt_value():
    parser = make_parser("foo.bar = 35")
    ctx = parser.assign_stmt()

    dizzy = Dizzy("test.ato")
    results = dizzy.visitAssign_stmt(ctx)
    assert len(results) == 1
    assert results[0] == (('foo', 'bar'), 35)

def test_visitAssign_stmt_string():
    parser = make_parser('foo.bar = "baz"')
    ctx = parser.assign_stmt()

    dizzy = Dizzy("test.ato")
    results = dizzy.visitAssign_stmt(ctx)
    assert len(results) == 1
    assert results[0] == (('foo', 'bar'), "baz")

def test_visitNew_stmt():
    parser = make_parser("new Bar")
    ctx = parser.new_stmt()

    dizzy = Dizzy("test.ato")
    results = dizzy.visitNew_stmt(ctx)
    assert results == Object(supers=("Bar",), locals_=())

def test_visitModule1LayerDeep():
    tree = parse_as_file(
        """
        component comp1:
            signal signal_a
            signal signal_b
            signal_a ~ signal_b
        """
    )
    dizzy = Dizzy("test.ato")
    results = dizzy.visitFile_input(tree)
    assert results == Object(supers=MODULE, locals_=(
        (('comp1',), Object(supers=COMPONENT,
        locals_= (
            (('signal_a',), Object(supers=SIGNAL)),
            (('signal_b',), Object(supers=SIGNAL)),
            (None, Link(source=('signal_a',), target=('signal_b',)),)
        ))),
    ))

def test_visitModule_pin_to_signal():
    tree = parse_as_file(
        """
        component comp1:
            signal signal_a ~ pin p1
        """
    )
    dizzy = Dizzy("test.ato")
    results = dizzy.visitFile_input(tree)
    assert results == Object(supers=MODULE, locals_=(
        (('comp1',), Object(supers=COMPONENT,
        locals_= (
            (None, Link(source=('signal_a',), target=('p1',)),),
            (('signal_a',), Object(supers=SIGNAL)),
            (('p1',), Object(supers=PIN))
        ))),
    ))

def test_visitModule0LayerDeep():
    tree = parse_as_file(
        """
        component comp1:
            signal signal_a
        """
    )
    dizzy = Dizzy("test.ato")
    results = dizzy.visitFile_input(tree)
    assert results == Object(supers=MODULE, locals_=(
        (
            ('comp1',), Object(supers=COMPONENT, locals_=((('signal_a',), Object(supers=SIGNAL)),))
        ),
    ))
