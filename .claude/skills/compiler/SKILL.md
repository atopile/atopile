---
name: Compiler
description: "How the atopile compiler builds and links TypeGraphs from `.ato` (ANTLR front-end → AST → TypeGraph → Linker → DeferredExecutor), plus the key invariants and test entrypoints."
---

# Compiler Module

The compiler builds a **linked, self-contained TypeGraph** from `.ato` sources. Export/manufacturing artifacts are handled later by build steps/exporters; the compiler’s job is parsing + typegraph construction + linking.

Start with:
- `src/atopile/compiler/README.md` (stage overview + example usage)
- `src/atopile/compiler/parser/README.md` (how to regenerate ANTLR output)

## Quick Start

Build a single `.ato` file into a linked TypeGraph (and instantiate its entrypoint):

```python
import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
from atopile.compiler.build import Linker, StdlibRegistry, build_file
from atopile.compiler.deferred_executor import DeferredExecutor
from atopile.config import config

g = graph.GraphView.create()
tg = fbrk.TypeGraph.create(g=g)
stdlib = StdlibRegistry(tg)
linker = Linker(config, stdlib, tg)

result = build_file(g=g, tg=tg, import_path="app.ato", path="path/to/app.ato")
linker.link_imports(g=g, state=result.state)
DeferredExecutor(g=g, tg=tg, state=result.state, visitor=result.visitor).execute()

app_type = result.state.type_roots["ENTRYPOINT"]
app_root = tg.instantiate_node(type_node=app_type, attributes={})
app = fabll.Node.bind_instance(app_root)
```

## Relevant Files

- Core pipeline:
  - `src/atopile/compiler/build.py` (`build_file`, `build_source`, `Linker`, `StdlibRegistry`, stage helpers)
  - `src/atopile/compiler/parse.py` (ANTLR parse + error listener → `UserSyntaxError`)
  - `src/atopile/compiler/antlr_visitor.py` (ANTLR CST → internal AST graph with source info)
  - `src/atopile/compiler/ast_visitor.py` (AST → TypeGraph “preliminary” construction)
  - `src/atopile/compiler/gentypegraph.py` (typegraph generation utilities + import refs)
  - `src/atopile/compiler/deferred_executor.py` (terminal stage: inheritance/retypes/for-loops)
- Parser frontend:
  - `src/atopile/compiler/parser/` (`AtoLexer.g4`, `AtoParser.g4`, generated Python)

## Dependants (Call Sites)

- **CLI (`src/atopile/cli/build.py`)**: Calls the compiler to build the project.
- **LSP (`src/atopile/lsp/lsp_server.py`)**: Builds per-document graphs and keeps the last successful result for completions/hover.

## How to Work With / Develop / Test

### Core Concepts
- **ANTLR front-end**: parse `.ato` into an ANTLR parse tree; syntax errors are converted to `UserSyntaxError`.
- **AST graph**: `ANTLRVisitor` converts ANTLR output into internal AST nodes (FabLL nodes with source info).
- **TypeGraph build**: AST visitor emits a preliminary TypeGraph.
- **Linking**: `Linker` resolves imports, executes inheritance ordering, applies retypes, and prepares a self-contained compilation unit.
- **Deferred execution (terminal)**: `DeferredExecutor.execute()` runs operations that require resolved types (inheritance, retypes, for-loops).

### Development Workflow
1) Grammar changes:
   - edit `src/atopile/compiler/parser/AtoLexer.g4` / `AtoParser.g4`
   - regenerate (see `src/atopile/compiler/parser/README.md`)
2) Language features:
   - CST → AST: `src/atopile/compiler/antlr_visitor.py`
   - AST → TypeGraph: `src/atopile/compiler/ast_visitor.py` / `gentypegraph.py`
3) Linking/terminal behavior:
   - `src/atopile/compiler/build.py` / `src/atopile/compiler/deferred_executor.py`

### Testing
- Compiler tests: `pytest test/compiler -q`
- Linker behavior: `pytest test/compiler/test_linker.py -q`
- End-to-end smoke: `pytest test/test_end_to_end.py -q`

## Best Practices
- Keep errors source-attached: raise `DslRichException`/`UserException` with AST source info when possible.
- Watch graph lifetimes: most entrypoints accept `(g, tg)` explicitly; ensure you destroy `GraphView` in long-running processes (LSP does this).
