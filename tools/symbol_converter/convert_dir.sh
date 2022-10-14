#!/bin/bash

dir=$1
out=$2
mkdir -p $out

run() {
    i=$1
    name=$(basename $i .kicad_sym | sed -r "s/^([^a-zA-Z])/_\1/")
    echo $name
    python3 $(dirname $0)/main.py $i $out/$name.py || echo "Failed running for $i" && exit 1
} 

for i in $dir/*.kicad_sym; do
    run $i &
done

echo "Waiting for jobs to finish..."
wait
echo "Done"