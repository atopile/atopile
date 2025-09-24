from collections.abc import Iterator
from pathlib import Path

import atopile.compiler.ir_types as ir
from atopile.compiler.ir_builder import build_file
from faebryk.libs.util import KeyErrorNotFound


def file_loc_key(node: ir.CompilerNode) -> ir.FileLocation:
    try:
        (source_chunk,) = node.get_children(types=ir.SourceChunk, direct_only=True)
        return source_chunk.file_location
    except ValueError:
        return ir.FileLocation(0, 0, 0, 0)


def _iter_nodes(node: ir.CompilerNode) -> Iterator[ir.CompilerNode]:
    """
    Pre-order traversal of CompilerNode tree, yielding (and terminating on) nodes with a
    SourceChunk child
    """
    if node.get_children(types=ir.SourceChunk, direct_only=True):
        yield node
    else:
        for child in sorted(
            node.get_children(direct_only=True, types=ir.CompilerNode), key=file_loc_key
        ):
            yield from _iter_nodes(child)


def print_tree(example: ir.CompilerNode) -> None:
    def _renderer(n: ir.CompilerNode) -> str:
        try:
            text = n.get_first_child_of_type(ir.SourceChunk, direct_only=True).text
        except KeyErrorNotFound:
            text = ""

        if "\n" in text:
            text = text.split("\n")[0] + "..."

        return f"{type(n).__name__}: `{text}`"

    print(example.get_tree(types=ir.CompilerNode).pretty_print(node_renderer=_renderer))


def visualize(example: ir.CompilerNode):
    from atopile.compiler.ir_viewer import visualize

    visualize(example)


if __name__ == "__main__":
    import sys

    example_file = build_file(Path("examples/esp32_minimal/esp32_minimal.ato"))
    print_tree(example_file)

    if len(sys.argv) > 1 and sys.argv[1] == "visualize":
        visualize(example_file)
