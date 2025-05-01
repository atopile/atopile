#!/bin/bash

file=$(realpath "$1")
shift

cd "$(dirname "$0")"
antlr4-parse AtoParser.g4 AtoLexer.g4 file_input -gui $@ < "$file" 
