#!/bin/bash

DIR=$(mktemp -d || exit)
mode=$1
shift

if [ "$mode" == "cprofile" ]; then

    pstats=$DIR/output.pstats
    dot=$DIR/output.dot

    python -m cProfile -o $pstats "$@"
    gprof2dot -f pstats $pstats -o $dot || exit

    running_in_vscode_terminal=$(echo $TERM_PROGRAM | grep -i "vscode" | wc -l)
    code_bin=$(which code)
    if [ $? -eq 0 ]; then
        count_vscode_instance_running=$(ps aux | grep -i "/code" | grep -v grep | wc -l)
    fi

    if [ $running_in_vscode_terminal -eq 1 ]; then
        code $dot
    elif [ $count_vscode_instance_running -gt 0 ]; then
        $code_bin -r $dot
    else
        dot -Tpng -o $DIR/output.png $dot || exit
        xdg-open $DIR/output.png &
    fi

    snakeviz $pstats || exit
    echo $DIR/output.dot

elif [ "$mode" == "viztracer" ]; then
    viztracer --open -o $DIR/output.json "$@"
elif [ "$mode" == "pyinstrument" ]; then
    pyinstrument -r text "$@"
else
    echo "Invalid mode: $mode"
fi
