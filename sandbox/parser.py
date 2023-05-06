from antlr4 import CommonTokenStream, FileStream
from atopile.parser.AtopileLexer import AtopileLexer
from atopile.parser.AtopileParser import AtopileParser

from pathlib import Path

test_file = Path(__file__).parent / "test.ato"

input = FileStream(test_file)
lexer = AtopileLexer(input)
stream = CommonTokenStream(lexer)
parser = AtopileParser(stream)
tree = parser.file_input()
print(tree.toStringTree(recog=parser))


