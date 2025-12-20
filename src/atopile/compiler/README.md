# ato compiler

The ato compiler is responsible for converting the ato DSL into a faebryk type-graph.

## Overview of stages

As currently implemented — pending bespoke lexer/parser.

- ANTLR4 lexer + parser (`parser/`)
  Converts DSL into an ANTLR4 AST.

- faebryk graph AST (`antlr_visitor.py`)
  Generates a faebryk graph AST from the ANTLR4 AST.

- Initial faebryk type-graph (`ast_visitor.py`, `gentypegraph.py`)
  Generates a preliminary faebryk type-graph from the faebryk graph AST.

- Linker (`build.py`)
  Resolves imports and links type-graphs to generate a fully-specified self-contained compilation unit.

- Finalised faebryk type-graph (`ast_visitor.py:execute_pending`)
  After linking, executes deferred operations that require resolved types:
  1. Inheritance resolution — copies parent structure into derived types
  2. Retype operations — updates type references for `target -> NewType` statements
  3. For-loop execution — iterates over containers with inherited/retyped fields

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

# execute deferred operations (inheritance, retypes, for-loops)
result.visitor.execute_pending()

# instantiate
app_type = result.state.type_roots["ENTRYPOINT"]
app = result.state.type_graph.instantiate_node(type_node=app_type, attributes={})
```
