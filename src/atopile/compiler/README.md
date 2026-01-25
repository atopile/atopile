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

- Finalised faebryk type-graph (`deferred_executor.py`)
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
typegraph = TypeGraph.create(graph)
linker = Linker(config, StdlibRegistry(typegraph), typegraph)

# build a file
result = build_file(graph, typegraph, import_path=Path("path/to/file.ato"), path=Path("path/to/file.ato"))

# resolve + build imports and link
linker.link_imports(graph, result.state)

# execute deferred operations (inheritance, retypes, for-loops)
DeferredExecutor(g=graph, tg=typegraph, state=result.state, visitor=result.visitor).execute()

# instantiate
app_type = result.state.type_roots["ENTRYPOINT"]
app_node = typegraph.instantiate_node(type_node=app_type, attributes={})

# as fabll Node for convenience
app = fabll.Node.bind_instance(app_node)
```
