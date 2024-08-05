import pytest

from antlr4 import InputStream

from atopile.front_end import DocStringVisitor
from atopile.parse import make_parser
from atopile.parser.AtopileParser import AtopileParser


def test_doc_string():
    src_code = '''
module Test:
    """
    This is a test module
    """
    pass'''
    input = InputStream(src_code)
    input.name = "<inline>"
    parser = make_parser(input)
    block_def = parser.blockdef()
    assert DocStringVisitor().get_doc_string(block_def) == "This is a test module"


def test_no_doc_string():
    src_code = '''
module Test:
    pass'''
    input = InputStream(src_code)
    input.name = "<inline>"
    parser = make_parser(input)
    block_def = parser.blockdef()
    assert DocStringVisitor().get_doc_string(block_def) == ""


def test_multiline_doc_string():
    src_code = '''
module Test:
    """
    This is a test module
    with multiple lines
    three, in fact!
    """
    pass'''

    input = InputStream(src_code)
    input.name = "<inline>"
    parser = make_parser(input)
    block_def = parser.blockdef()
    assert DocStringVisitor().get_doc_string(block_def) == "This is a test module\nwith multiple lines\nthree, in fact!"


def test_multiline_doc_string_first_line_on_quotes():
    src_code = '''
module Test:
    """This is a test module
    with multiple lines
    three, in fact!
    """
    pass'''

    input = InputStream(src_code)
    input.name = "<inline>"
    parser = make_parser(input)
    block_def = parser.blockdef()
    assert DocStringVisitor().get_doc_string(block_def) == "This is a test module\nwith multiple lines\nthree, in fact!"


def test_multiline_doc_string_both_lines_on_quotes():
    src_code = '''
module Test:
    """This is a test module
    with multiple lines
    three, in fact!"""
    pass'''

    input = InputStream(src_code)
    input.name = "<inline>"
    parser = make_parser(input)
    block_def = parser.blockdef()
    assert DocStringVisitor().get_doc_string(block_def) == "This is a test module\nwith multiple lines\nthree, in fact!"


def test_multiline_doc_string_last_line_on_quotes():
    src_code = '''
module Test:
    """
    This is a test module
    with multiple lines
    three, in fact!"""
    pass'''

    input = InputStream(src_code)
    input.name = "<inline>"
    parser = make_parser(input)
    block_def = parser.blockdef()
    assert DocStringVisitor().get_doc_string(block_def) == "This is a test module\nwith multiple lines\nthree, in fact!"
