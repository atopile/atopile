# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest

def run_tests():
    runner = unittest.TextTestRunner()
    suite = unittest.TestLoader().discover(".", pattern="test_*.py")
    runner.run(suite)

if __name__ == '__main__':
    run_tests()