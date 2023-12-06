from atopile.model2.datamodel import (
    Object,
    LinkDef,
    Import,
    Replace,
    MODULE_REF,
    COMPONENT_REF,
    PIN_REF,
    SIGNAL_REF,
    INTERFACE_REF,
)
from rich.tree import Tree
from rich import print
from typing import Iterable

from atopile.model2.datatypes import Ref


def dot(strs: Iterable[str]) -> str:
    # if strs is a tuple with first element as an integer, return it as a string
    if isinstance(strs, tuple) and isinstance(strs[0], int):
        return str(strs[0])
    else:
        return ".".join(strs)


class Wendy:
    def get_label(self, name, super_refs: tuple[Ref], address=None):
        # Check the type of the node and return the label
        if MODULE_REF in super_refs:
            return f"🎁 {name} address: {address} (module)"
        elif COMPONENT_REF in super_refs:
            return f"⚙️ {name} (component)"
        elif SIGNAL_REF in super_refs:
            return f"⚡️ {name} (signal)"
        elif PIN_REF in super_refs:
            return f"📍 {name} (pin)"
        elif INTERFACE_REF in super_refs:
            return f"🔌 {name} (interface)"
        else:
            # find anything that is not a builtin
            friendly_supers = ", ".join(map(str, super_refs))
            return f"❓ {name} ({friendly_supers})"

    def parse_link(self, name, obj, parent_tree):
        parent_tree.add(dot(obj.source_ref) + " 🔗 " + dot(obj.target_ref) + " (Link)")

    def parse_replace(self, name, obj, parent_tree):
        parent_tree.add(dot(obj.original_ref) + " 👉 " + dot(obj.replacement_ref) + " (Replace)")

    def parse_import(self, name, obj, parent_tree):
        parent_tree.add(dot(obj.what_ref) + " 📦 " + obj.from_name + " (Import)")

    def visit(self, ref: None | tuple[str], input_node, rich_tree: Tree):
        # Check the input node type and call the appropriate function
        if isinstance(input_node, LinkDef):
            self.parse_link(input_node.source_ref, input_node, rich_tree)
        elif isinstance(input_node, Replace):
            self.parse_replace(input_node.original_ref, input_node, rich_tree)
        elif isinstance(input_node, Import):
            self.parse_import(input_node.what_ref, input_node, rich_tree)
        elif isinstance(input_node, str):
            rich_tree.add(ref[0] + " = " + input_node)
        # objects have locals, which can be nested, so we need to recursively call visit
        elif isinstance(input_node, Object):
            if ref is None:
                name = "Unknown"
            else:
                name = str(ref[0])
            # add a label for the object
            subtree = rich_tree.add(self.get_label(name, input_node.supers_refs, input_node.address))
            if input_node.locals_ == ():
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
