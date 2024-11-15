#!/bin/bash

parent_dir=$(dirname "$0")/..
test_dir="$parent_dir/test"

# find all files in test_dir ending in .py
# make sure the filenames are unique
find "$test_dir" -type f -name "*.py" -exec basename {} \; | sort | uniq -d
