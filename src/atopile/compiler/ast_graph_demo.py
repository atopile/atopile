from pathlib import Path
from typing import Literal

import atopile.compiler.ast_types as AST
from atopile.compiler.ast_graph import build_file
from atopile.compiler.graph_mock import BoundNode, EdgeSource, EdgeType, Node

# def print_tree(graph: GraphView) -> None:
#     def _renderer(n: Node) -> str:
#         try:
#             (source_chunk,) = n.get_children(types=AST.SourceChunk, direct_only=True)
#             text = source_chunk.text
#         except ValueError:
#             text = ""

#         if "\n" in text:
#             text = text.split("\n")[0] + "..."

#         return f"{type(n).__name__}: `{text}`"

#     print(example.get_tree(types=AST.ASTNode).pretty_print(node_renderer=_renderer))


def visualize(example: Node):
    from atopile.compiler.ast_viewer import visualize

    visualize(example)


def get_source_text(n: BoundNode) -> str | None:
    try:
        (source_chunk,) = n.get_neighbours(edge_type=EdgeSource.get_tid())
        return AST.SourceChunk.get_text(source_chunk)
    except ValueError:
        return None


def get_type_name(n: BoundNode) -> str | None:
    try:
        (type_node,) = n.get_neighbours(edge_type=EdgeType.get_tid())
        return AST.ASTType.get_name(type_node)
    except ValueError:
        return None


if __name__ == "__main__":
    ast_root = build_file(Path("examples/esp32_minimal/esp32_minimal.ato"))

    def _renderer(n: BoundNode) -> str:
        text = get_source_text(n) or ""
        if "\n" in text:
            text = text.split("\n")[0] + "..."

        type_name = get_type_name(n) or type(n.node).__name__
        return f"{type_name}: `{text}`"

    ast_root.print_tree(renderer=_renderer)

    # if len(sys.argv) > 1 and sys.argv[1] == "visualize":
    #     visualize(ast_graph)
