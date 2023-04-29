#%%
from antlr4 import CommonTokenStream, FileStream, InputStream
from atopile.language.Python3Lexer import Python3Lexer
from atopile.language.Python3Parser import Python3Parser
# from atopile.language.ChatLexer import ChatLexer
# from atopile.language.ChatParser import ChatParser

from pathlib import Path

#%%
input = InputStream("a=1\n")
lexer = Python3Lexer(input)
stream = CommonTokenStream(lexer)
parser = Python3Parser(stream)
tree = parser.single_input()
print(tree.toStringTree(recog=parser))
# %%

