# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os

logger = logging.getLogger(__name__)


def in_test() -> bool:
    return "PYTEST_CURRENT_TEST" in os.environ
