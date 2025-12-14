# atopile Parser

This directory contains ANTLR grammar files (`.g4`) and generated Python parser code for parsing `.ato` files.

## Building this

cd to the `src/atopile/compiler/parser` directory and run the following command:

`antlr4 -visitor -no-listener -Dlanguage=Python3 AtoLexer.g4 AtoParser.g4`

## Troubleshooting

- Make sure you're running platform-native homebrew
- Ensure java is installed
