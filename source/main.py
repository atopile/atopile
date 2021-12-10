#!/bin/env python

# Copyright (c) 2021 ITENG
# SPDX-License-Identifier: MIT
import sys
import logging
import tests
import experiment


def main(argc, argv, argi):
    print("faebryk dev v0.0")
    logging.basicConfig(level=logging.INFO)

    ok = tests.run_tests()
    print("Tests ok?", ok)

    print("Running experiment")
    experiment.run_experiment()

if __name__ == "__main__":
    main(len(sys.argv), sys.argv, iter(sys.argv))