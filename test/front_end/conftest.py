import pytest

from atopile.front_end import Bob


@pytest.fixture
def bob() -> Bob:
    return Bob()
