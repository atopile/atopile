import os

import pytest

from faebryk.libs.util import get_module_from_path, hash_string, import_from_path


# Create test fixtures
@pytest.fixture
def temp_module(tmp_path):
    """Create a temporary Python module for testing"""
    module_path = tmp_path / "test_module.py"
    module_content = """
TEST_CONSTANT = "test_value"
def test_function():
    return "test_result"
"""
    module_path.write_text(module_content, encoding="utf-8")
    return module_path


@pytest.fixture
def temp_package(tmp_path):
    """Create a temporary Python package for testing"""
    package_dir = tmp_path / "test_package"
    package_dir.mkdir()

    init_path = package_dir / "__init__.py"
    init_path.write_text("PACKAGE_CONSTANT = 'package_value'", encoding="utf-8")

    submodule_path = package_dir / "submodule.py"
    submodule_path.write_text("SUB_CONSTANT = 'sub_value'", encoding="utf-8")

    return package_dir


@pytest.fixture
def temp_non_python_file(tmp_path):
    """Create a temporary non-Python file for testing"""
    non_python_path = tmp_path / "non_python_file.txt"
    non_python_path.write_text("This is a non-Python file", encoding="utf-8")
    return non_python_path


def test_hash_string():
    """Test that hash_string produces consistent results"""
    test_str = "test string"
    result1 = hash_string(test_str)
    result2 = hash_string(test_str)

    assert isinstance(result1, str)
    assert len(result1) > 0
    assert result1 == result2


def test_hash_string_different_inputs():
    """Test that hash_string produces different results for different inputs"""
    test_str1 = "test string 1"
    test_str2 = "test string 2"
    result1 = hash_string(test_str1)
    result2 = hash_string(test_str2)

    assert result1 != result2


def test_get_module_from_path_not_imported(temp_module):
    """Test get_module_from_path returns None for non-imported module"""
    result = get_module_from_path(temp_module)
    assert result is None


def test_get_module_from_path_imported(temp_module):
    """Test get_module_from_path returns module after import"""
    # First import the module
    module = import_from_path(temp_module)

    # Then try to get it
    result = get_module_from_path(temp_module)
    assert result is not None
    assert result == module
    assert hasattr(result, "TEST_CONSTANT")
    assert result.TEST_CONSTANT == "test_value"


def test_import_from_path_basic(temp_module):
    """Test basic module import functionality"""
    module = import_from_path(temp_module)

    assert module is not None
    assert hasattr(module, "TEST_CONSTANT")
    assert module.TEST_CONSTANT == "test_value"
    assert hasattr(module, "test_function")
    assert module.test_function() == "test_result"


def test_import_from_path_with_attr(temp_module):
    """Test importing specific attribute from module"""
    func = import_from_path(temp_module, "test_function")
    assert callable(func)
    assert func() == "test_result"


def test_import_from_path_nonexistent():
    """Test importing nonexistent module raises ImportError"""
    with pytest.raises(FileNotFoundError):
        import_from_path("nonexistent_module.py")


def test_import_from_path_not_python(temp_non_python_file):
    """Test importing non-Python file raises ImportError"""
    with pytest.raises(ImportError):
        import_from_path(temp_non_python_file)


def test_import_from_path_invalid_attr(temp_module):
    """Test importing nonexistent attribute raises AttributeError"""
    with pytest.raises(AttributeError):
        import_from_path(temp_module, "nonexistent_attr")


def test_import_from_path_reimport(temp_module):
    """Test that reimporting same module returns same instance"""
    module1 = import_from_path(temp_module)
    module2 = import_from_path(temp_module)

    assert module1 is module2
    assert id(module1) == id(module2)


def test_import_from_path_package(temp_package):
    """Test importing from a package"""
    module = import_from_path(temp_package / "__init__.py")

    assert module is not None
    assert hasattr(module, "PACKAGE_CONSTANT")
    assert module.PACKAGE_CONSTANT == "package_value"


def test_path_normalization(temp_module):
    """Test that different path formats resolve to same module"""
    # Get absolute path
    abs_path = temp_module.absolute()

    # Import using different path formats
    module1 = import_from_path(abs_path)
    module2 = import_from_path(str(abs_path))
    module3 = import_from_path(os.path.relpath(abs_path))

    assert module1 is module2 is module3
