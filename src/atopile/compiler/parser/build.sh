#!/bin/bash

cd "$(dirname "$0")"
antlr4 -long-messages -visitor -no-listener -Dlanguage=Python3 $@ AtoLexer.g4 AtoParser.g4
