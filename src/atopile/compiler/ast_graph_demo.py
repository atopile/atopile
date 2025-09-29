from pathlib import Path

import atopile.compiler.ast_types as AST
from atopile.compiler.ast_graph import build_file


def print_tree(example: AST._Node) -> None:
    def _renderer(n: AST._Node) -> str:
        try:
            (source_chunk,) = n.get_children(types=AST.SourceChunk, direct_only=True)
            text = source_chunk.text
        except ValueError:
            text = ""

        if "\n" in text:
            text = text.split("\n")[0] + "..."

        return f"{type(n).__name__}: `{text}`"

    print(example.get_tree(types=AST.ASTNode).pretty_print(node_renderer=_renderer))


def visualize(example: AST._Node):
    from atopile.compiler.ast_viewer import visualize

    visualize(example)


if __name__ == "__main__":
    import sys

    example_file = build_file(Path("examples/esp32_minimal/esp32_minimal.ato"))
    print_tree(example_file)

    if len(sys.argv) > 1 and sys.argv[1] == "visualize":
        visualize(example_file)
