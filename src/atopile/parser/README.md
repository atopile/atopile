# So I'll thank myself later

## Installing ANTLR

1. Make sure you're running native brew (an issue if you're on OSx with Rosetta - because you mightn't notice)
2. Install java
3. `pip install antlr4-tools`

I thiiiiink that should work, but it was a bit of a PITA and there's a chance I missed something.

## Building this

cd to the `src/atopile/parser` directory and run the following command:

`antlr4 -visitor -no-listener -Dlanguage=Python3 AtopileLexer.g4 AtopileParser.g4`

