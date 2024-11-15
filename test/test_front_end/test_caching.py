import textwrap
from pathlib import Path

from atopile import front_end, parse
from atopile.front_end import parser

PRJ = Path(__file__).parent / "prj"
FILE = PRJ / "test.ato"
MODULE = str(FILE) + ":Test"


def test_caching():
    parser.cache[str(FILE)] = parse.parse_text_as_file(
        textwrap.dedent(
            """
            module Test:
                a = 1
                b = 2
            """
        ),
        MODULE,
    )
    root_1 = front_end.lofty.get_instance(MODULE)

    # Make sure it's parsed properly
    assert root_1.assignments["a"][0].value == 1

    # Make sure it's consistent and cached
    assert root_1 is front_end.lofty.get_instance(MODULE)

    # Clear it out, to make sure it's re-parsed
    front_end.reset_caches(MODULE)

    # Parse something else to make sure it's re-parsed
    root_2 = front_end.lofty.get_instance(MODULE)
    assert root_1 is not root_2
