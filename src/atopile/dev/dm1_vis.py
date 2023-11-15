from atopile.model2.datamodel1 import (
    Object,
    Link,
    Import,
    Replace,
    MODULE,
    COMPONENT,
    PIN,
    SIGNAL,
    INTERFACE,
    NOTHING,
)
from rich.tree import Tree
from rich import print
from typing import Iterable


def dot(strs: Iterable[str]) -> str:
    # if strs is a tuple with first element as an integer, return it as a string
    if isinstance(strs, tuple) and isinstance(strs[0], int):
        return str(strs[0])
    else:
        return ".".join(strs)


class Wendy:
    def get_label(self, name, supers):
        # Check the type of the node and return the label
        if supers == MODULE:
            return f"🎁 {name} (module)"
        elif supers == COMPONENT:
            return f"⚙️ {name} (component)"
        elif supers == SIGNAL:
            return f"⚡️ {name} (signal)"
        elif supers == PIN:
            return f"📍 {name} (pin)"
        elif supers == INTERFACE:
            return f"🔌 {name} (interface)"
        else:
            return f"❓ {name} (unknown)"

    def parse_link(self, name, obj, parent_tree):
        parent_tree.add(dot(obj.source) + " 🔗 " + dot(obj.target) + " (Link)")

    def parse_replace(self, name, obj, parent_tree):
        parent_tree.add(dot(obj.original) + " 👉 " + dot(obj.replacement) + " (Replace)")

    def parse_import(self, name, obj, parent_tree):
        parent_tree.add(dot(obj.what) + " 📦 " + obj.from_ + " (Import)")

    def visit(self, ref: None | tuple[str], input_node, rich_tree: Tree):
        # Check the input node type and call the appropriate function
        if isinstance(input_node, Link):
            self.parse_link(input_node.source, input_node, rich_tree)
        elif isinstance(input_node, Replace):
            self.parse_replace(input_node.original, input_node, rich_tree)
        elif isinstance(input_node, Import):
            self.parse_import(input_node.what, input_node, rich_tree)
        elif isinstance(input_node, str):
            rich_tree.add(ref[0] + " = " + input_node)
        # objects have locals, which can be nested, so we need to recursively call visit
        elif isinstance(input_node, Object):
            if ref is None:
                name = "Unknown"
            else:
                name = str(ref[0])
            # add a label for the object
            subtree = rich_tree.add(self.get_label(name, input_node.supers))
            if input_node.locals_ == NOTHING:
                label = "📦 Sentinel.Nothing (Empty)"
                rich_tree.add(label)
            else:
                for ref, obj in input_node.locals_:
                    self.visit(ref, obj, subtree)
        else:
            # pass
            raise TypeError(f"Unknown type {type(input_node)}")
        return rich_tree

    def build_tree(self, dm1_tree: Object):
        """
        Build a tree structure using rich.tree
        dm1_tree: Object
        """
        # Create a tree structure using rich.tree
        tree = Tree("🌳 stuff")
        return self.visit(("Project",), dm1_tree, tree)

    def print_tree(self, dm1_tree: Object):
        # Create a tree structure using rich.tree
        tree = self.build_tree(dm1_tree)
        print(tree)


# =========================
# example usage
# # Display the tree
# dm1 = Object(
#         supers=MODULE,
#         locals_=(
#             (("comp1",), Object(
#                 supers=COMPONENT,
#                 locals_=((("comp1","comp2"), Object(
#                 supers=COMPONENT,
#                 locals_=(
#                     (("signal_a",), Object(
#                         supers=SIGNAL,
#                         locals_=()
#                     )),(("signal_b",), Object(
#                         supers=SIGNAL,
#                         locals_=()
#                     ))
#                 )
#             )),
#                     (("signal_a",), Object(
#                         supers=SIGNAL,
#                         locals_=()
#                     )),(("signal_b",), Object(
#                         supers=SIGNAL,
#                         locals_=()
#                     ))
#                 )
#             )),
#             (("comp1",), Object(
#                 supers=COMPONENT,
#                 locals_=(
#                     (("interface1",), Object(
#                         supers=INTERFACE,
#                         locals_=()
#                     )),(("pin1",), Object(
#                         supers=PIN,
#                         locals_=()
#                     ))
#                 )
#             )),
#         )
# )
# tree_builder = Wendy()
# tree = tree_builder.build_tree(dm2)
# print(tree)
