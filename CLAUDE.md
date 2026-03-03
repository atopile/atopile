# Overview

You are inside the atopile monorepo.
atopile is an open-source EDA tool.
ato is a domain-specific language that is created to define electronics in code.
Everything is modeled in the graph.
There multiple layers and modules:
zig, graph, faebryk, fabll, domain-layer, build-server, frontend

## Modules & Entry Points

| Module           | Location                                  | Entry Point                                                                      |
| ---------------- | ----------------------------------------- | -------------------------------------------------------------------------------- |
| **zig**          | `src/faebryk/core/zig/`                   | `build.zig` → compiles to `pyzig` extension                                      |
| **graph**        | `src/faebryk/core/zig/src/graph/`         | `lib.zig` (bindings in `src/faebryk/core/zig/src/python/graph/manual/graph.pyi`) |
| **faebryk**      | `src/faebryk/core/zig/src/faebryk`        | `lib.zig` (bindings in `src/faebryk/core/zig/src/python/faebryk/manual`)         |
| **fabll**        | `src/faebryk/core/node.py`                |                                                                                  |
| **domain-layer** | `src/faebryk/exporters` and `src/atopile` | `cli/cli.py:main()` (Typer CLI)                                                  |
| **build-server** | `src/atopile/server/`                     | `__main__.py` (FastAPI)                                                          |
| **frontend**     | `src/vscode-atopile/` + `src/ui-server/`  | `extension.ts` / `dev.tsx` (React+Vite)                                          |

# Programming languages

- zig for the core (`.zig`)
- python for the domain-layer (`.py` / `.pyi`)
- ato for the library and applications (`.ato`)
- typescript for the ui (`.ts`, `.tsx`)

# Tooling

- testing is done via `ato dev test`

# SKILLS

For detailed explanations of submodules read the correspondig skill.
Skills are located in `.claude/skills/`.

```
.claude/skills
├── agent
│ └── SKILL.md
├── ato-language
│ ├── EXTENSION.md
│ └── SKILL.md
├── code-review
│ └── SKILL.md
├── compiler
│ └── SKILL.md
├── dev
│ └── SKILL.md
├── domain-layer
│ └── SKILL.md
├── fabll
│ └── SKILL.md
├── faebryk
│ └── SKILL.md
├── frontend
│ └── SKILL.md
├── graph
│ └── SKILL.md
├── library
│ └── SKILL.md
├── lsp
│ └── SKILL.md
├── pyzig
│ └── SKILL.md
├── sexp
│ └── SKILL.md
├── atopile-skills
│ └── SKILL.md
└── solver
  └── SKILL.md
```
