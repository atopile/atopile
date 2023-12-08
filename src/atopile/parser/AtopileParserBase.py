from antlr4 import Parser

class AtopileParserBase(Parser):

    def CannotBePlusMinus(self) -> bool:
        return True

    def CannotBeDotLpEq(self) -> bool:
        return True
