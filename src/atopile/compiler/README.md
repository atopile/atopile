# ato DSL compiler

The ato DSL compiler is responsible for converting the ato DSL into a faebryk TypeGraph.

## Overview of stages

As currently implemented — pending bespoke lexer/parser.

- ANTLR4 lexer + parser (`parser/`)
  Converts DSL into an ANTLR4 AST.

- faebryk graph AST (`antlr_visitor.py`, `ast_visitor.py`, `gentypegraph.py`)
  Generates a faebryk graph AST from the ANTLR4 AST.

- faebryk type graph (TODO)
  Links graph ASTs to generate a fully-specified self-contained compilation unit.
  This is a terminal stage for some use-cases (e.g. LSP, docs generation).

- faebryk design graph (TODO)
  Constructs full design representation graph from type graph.




The compiler is responsible for:

- Parsing the ato DSL into a native compiler graph.
- Validating the compiler graph.
- Generating a native compiler graph.
