from pathlib import Path

import atopile.compiler.ast_types as AST
from atopile.compiler.ast_graph import build_file
from atopile.compiler.graph_mock import BoundNode, NodeHelpers
from faebryk.core.zig.gen.faebryk.node_type import EdgeType
from faebryk.core.zig.gen.faebryk.source import EdgeSource


def get_source_text(n: BoundNode) -> str | None:
    try:
        (source_chunk,) = NodeHelpers.get_neighbours(n, EdgeSource.get_tid())
    except ValueError:
        return None
    return AST.SourceChunk.get_text(source_chunk)


def get_type_name(n: BoundNode) -> str | None:
    try:
        (type_node,) = NodeHelpers.get_neighbours(n, EdgeType.get_tid())
        return AST.ASTType.get_name(type_node)
    except ValueError:
        return None


def truncate_text(text: str) -> str:
    if "\n" in text:
        return text.split("\n")[0] + "..."
    return text


def renderer(n: BoundNode) -> str:
    type_name = get_type_name(n) or type(n.node).__name__

    text = truncate_text(get_source_text(n) or "")
    attrs = [f"{k}={truncate_text(str(v))}" for k, v in n.node().get_attrs().items()]

    return f"{type_name}({', '.join(attrs)}): `{text}`"


if __name__ == "__main__":
    ast_root = build_file(Path("examples/esp32_minimal/esp32_minimal.ato"))

    NodeHelpers.print_tree(ast_root, renderer=renderer)
