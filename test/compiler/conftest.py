import textwrap

import faebryk.core.node as fabll
from atopile.compiler.ast_visitor import STDLIB_ALLOWLIST
from atopile.compiler.build import BuildFileResult, Linker, StdlibRegistry, build_source
from atopile.compiler.deferred_executor import DeferredExecutor
from faebryk.core.faebrykpy import TypeGraph
from faebryk.core.graph import BoundNode, GraphView


def _link(
    g: GraphView, stdlib: StdlibRegistry, tg: TypeGraph, result: BuildFileResult
) -> None:
    linker = Linker(None, stdlib, tg)
    linker.link_imports(g, result.state)
    DeferredExecutor(g=g, tg=tg, state=result.state, visitor=result.visitor).execute()


def build_type(
    source: str, import_path: str | None = None, link: bool = False
) -> tuple[GraphView, TypeGraph, StdlibRegistry, BuildFileResult]:
    g = GraphView.create()
    tg = TypeGraph.create(g=g)
    stdlib = StdlibRegistry(tg)
    result = build_source(
        g=g, tg=tg, source=textwrap.dedent(source), import_path=import_path
    )

    if link:
        _link(g, stdlib, tg, result)

    return g, tg, stdlib, result


def build_instance(
    source: str,
    root: str,
    import_path: str | None = None,
    stdlib_extra: list[type[fabll.Node]] = [],
) -> tuple[GraphView, TypeGraph, StdlibRegistry, BuildFileResult, BoundNode]:
    import faebryk.library._F as F

    g = GraphView.create()
    tg = TypeGraph.create(g=g)
    stdlib_allowlist = STDLIB_ALLOWLIST.copy() | set(stdlib_extra)
    stdlib = StdlibRegistry(tg, allowlist=stdlib_allowlist)

    result = build_source(
        g=g,
        tg=tg,
        source=textwrap.dedent(source),
        import_path=import_path,
        stdlib_allowlist=stdlib_allowlist,
    )

    _link(g, stdlib, tg, result)

    app_root = tg.instantiate_node(
        type_node=result.state.type_roots[root], attributes={}
    )
    app = fabll.Node.bind_instance(app_root)
    F.Parameters.NumericParameter.infer_units_in_tree(app)

    return (
        g,
        tg,
        stdlib,
        result,
        app_root,
    )
