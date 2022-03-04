#!/bin/bash

file=$1
header="# This file is part of the faebryk project\n# SPDX-License-Identifier: MIT"

found_head="$(head -n2 $file)"
hash_1=$(echo -e "$found_head" | md5sum)
hash_2=$(echo -e "$header" | md5sum)

if [ "$hash_1" == "$hash_2" ]; then
    echo "Already found"
    exit 0
fi
echo -e "$file: Found:|$found_head|"

#TODO improve this script's robustness to a point where we can reliably call
#   the awk line to do the subsitution
#   For now this script is especially handy for checking whether the python
#   files have the license header in the top


exit 0


awk 'BEGIN{print ""}1' \
    $file | sponge $file
