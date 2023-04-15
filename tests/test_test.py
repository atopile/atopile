"""
This is a test tester to make sure the project's setup properly
"""

import pytest

def test_pass():
    pass

@pytest.mark.xfail
def test_fail():
    raise AssertionError
