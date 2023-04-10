import pyparsing as pp
import pytest

from atopile import ato_parser


def test_identifier():
    id = ato_parser.identifier
    # valid identifiers
    assert id.parseString('test_identifier3').as_list() == ['test_identifier3']
    assert id.parseString('_test_identifier3').as_list() == ['_test_identifier3']

    # invalid identifiers
    with pytest.raises(pp.ParseException):
        id.parseString('4test_identifier').as_list()
