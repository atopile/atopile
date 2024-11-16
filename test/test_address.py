import pytest

from atopile.address import (
    add_instance,
    add_instances,
    get_file,
    get_instance_names,
    get_instance_section,
    get_parent_instance_addr,
)


def test_get_file():
    # Test with a file address
    assert get_file("path/to/file.txt") == "path/to/file.txt"

    # Test with a file address containing special characters
    assert (
        get_file("path/to/file-with-special-chars.txt")
        == "path/to/file-with-special-chars.txt"
    )

    # Test with a file address containing a Windows drive letter
    assert get_file("C:/path/to/file.txt") == "C:/path/to/file.txt"

    # Test with an empty file address
    assert get_file("") == ""

    assert get_file("path/to/file.txt:a:b.c") == "path/to/file.txt"

    # Test with a file address containing special characters
    assert (
        get_file("path/to/file-with-special-chars.txt:a:b.c")
        == "path/to/file-with-special-chars.txt"
    )

    # Test with a file address containing a Windows drive letter
    assert get_file("C:/path/to/file.txt:a:b.c") == "C:/path/to/file.txt"


def test_get_instance_section():
    # Test with an address containing an instance section
    assert get_instance_section("path/to/file.txt:a:b.c") is None

    # Test with an address not containing an instance section
    assert get_instance_section("path/to/file.txt") is None

    # Test with an empty address
    assert get_instance_section("") is None

    # Test with an address containing a Windows drive letter
    assert get_instance_section("C:/path/to/file.txt:a::b.c") == "b.c"

    # Test with an address containing a Windows drive letter
    assert (
        get_instance_section("C:/path/to/file-with-special-chars.txt:a::b.c") == "b.c"
    )


def test_add_instance():
    assert add_instance("//a:b", "c") == "//a:b::c"

    with pytest.raises(Exception):
        add_instance("//a", "c")


def test_add_instances():
    assert add_instances("//a:b::", ["c", "d", "e"]) == "//a:b::c.d.e"
    assert add_instances("//a:b", ["c", "d", "e"]) == "//a:b::c.d.e"
    assert add_instances("//a:b", []) == "//a:b"


def test_get_parent():
    assert get_parent_instance_addr("//a:b::c") == "//a:b"
    assert get_parent_instance_addr("//a:b") is None
    assert get_parent_instance_addr("//a:b::") == "//a:b"
    assert get_parent_instance_addr("//a:b::c.d") == "//a:b::c"
    assert get_parent_instance_addr("//a:b::c.d.e") == "//a:b::c.d"


def test_get_instances():
    assert get_instance_names("//a:b::c.d.e") == ["c", "d", "e"]
    assert get_instance_names("//a:b") == []
    assert get_instance_names("//a:b::") == []
    assert get_instance_names("//a:b::c") == ["c"]
    assert get_instance_names("//a:b::c.d") == ["c", "d"]
