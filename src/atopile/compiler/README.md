# ato compiler

The ato compiler is responsible for converting the ato DSL into a faebryk type-graph.

## Overview of stages

As currently implemented — pending bespoke lexer/parser.

- ANTLR4 lexer + parser (`parser/`)
  Converts DSL into an ANTLR4 AST.

- faebryk graph AST (`antlr_visitor.py`)
  Generates a faebryk graph AST from the ANTLR4 AST.

- faebryk type-graph (`ast_visitor.py`, `gentypegraph.py`)
  Generates a faebryk type-graph from the faebryk graph AST.

- Linker (`build.py`)
  Resolves imports and links type-graphs to generate a fully-specified self-contained compilation unit.
  This is a terminal stage for some use-cases (e.g. LSP, docs generation).

The root node of the linked type-graph can then be instantiated to produce a design-graph.

## Usage

```python
# BYO graph
graph = GraphView.create()

# build the standard library
stdlib_tg, stdlib_registry = build_stdlib(graph)

# build a file
result = build_file(graph, "path/to/file.ato")

# resolve + build imports and link
linker = Linker(stdlib_registry, stdlib_tg)
linker.link_imports(graph, result.state)

# instantiate
app_type = result.state.type_roots["ENTRYPOINT"]
app = result.state.type_graph.instantiate_node(type_node=app_type, attributes={})
```
