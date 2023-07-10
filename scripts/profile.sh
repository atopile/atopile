#!/bin/bash

DIR=/tmp

python -m cProfile -o $DIR/output.pstats examples/resistors_and_nand.py --no-show-graph --no-make-graph
gprof2dot -f pstats $DIR/output.pstats -o $DIR/output.dot
dot -Tpng -o $DIR/output.png $DIR/output.dot
feh $DIR/output.png &