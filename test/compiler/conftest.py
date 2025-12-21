import textwrap

import faebryk.core.node as fabll
from atopile.compiler.ast_visitor import STDLIB_ALLOWLIST
from atopile.compiler.build import (
    BuildFileResult,
    Linker,
    StdlibRegistry,
    build_source,
    build_stage_2,
)
from faebryk.core.faebrykpy import TypeGraph
from faebryk.core.graph import BoundNode, GraphView


def _link(
    g: GraphView, stdlib: StdlibRegistry, tg: TypeGraph, result: BuildFileResult
) -> None:
    linker = Linker(None, stdlib, tg)
    build_stage_2(g=g, tg=tg, linker=linker, result=result)


def build_type(
    source: str,
    import_path: str | None = None,
    link: bool = False,
    validate: bool = True,
) -> tuple[GraphView, TypeGraph, StdlibRegistry, BuildFileResult]:
    from atopile.compiler import DslException
    from atopile.compiler.deferred_executor import DeferredExecutor
    from faebryk.libs.exceptions import accumulate

    g = GraphView.create()
    tg = TypeGraph.create(g=g)
    stdlib = StdlibRegistry(tg)
    result = build_source(
        g=g, tg=tg, source=textwrap.dedent(source), import_path=import_path
    )

    if link:
        linker = Linker(None, stdlib, tg)
        linker.link_imports(g, result.state)
        DeferredExecutor(
            g=g, tg=tg, state=result.state, visitor=result.visitor
        ).execute()

        if validate:
            with accumulate() as accumulator:
                for _, type_node in result.state.type_roots.items():
                    for _, message in tg.validate_type(type_node=type_node):
                        with accumulator.collect():
                            if message.startswith("duplicate:"):
                                field = message[len("duplicate:") :]
                                raise DslException(
                                    f"Field `{field}` is already defined"
                                )
                            else:
                                raise DslException(
                                    f"Field `{message}` is not defined in scope"
                                )

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
