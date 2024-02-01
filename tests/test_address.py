from atopile.address import get_file


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
