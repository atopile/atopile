#!/bin/env python

# Copyright (c) 2021 ITENG
# SPDX-License-Identifier: MIT
import sys
import logging

from sexp.sexp import gensexp
from sexp.test.sexptest import test_sexp


def main(argc, argv, argi):
    print("faebryk dev v0.0")
    logging.basicConfig(level=logging.INFO)

    test_sexp()




if __name__ == "__main__":
    main(len(sys.argv), sys.argv, iter(sys.argv))