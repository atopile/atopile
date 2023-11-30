import pytest
from unittest.mock import MagicMock

from atopile.model2.errors import AtoSyntaxError, write_errors_to_log
from atopile.dev.parse import parser_from_src_code

def test_syntax_error_processing():
    parser  = parser_from_src_code(
        """
        module test_module:
        +?@
        """
    )

    logger = MagicMock()

    with pytest.raises(AtoSyntaxError):
        with write_errors_to_log(logger=logger):
            parser.file_input()

    assert logger.error.call_count == 1
    assert logger.error.call_args[0][0].startswith("<empty>:2:0:")
