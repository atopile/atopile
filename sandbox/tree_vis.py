#%%
from atopile.dev.parse import parse_as_file
from atopile.model2.datamodel1 import Dizzy, Object, Link, Import, Replace, MODULE, COMPONENT, PIN, SIGNAL, INTERFACE
from rich import print
from atopile.dev.dm1_vis import Wendy

# %%
tree = parse_as_file(
    """
    module mod1:
        module comp1:
            module comp2:
                signal signal_a
    module mod_new:
        signal signal_b
        signal signal_a
    """
)
# %%
dizzy = Dizzy("test.ato")
dm1 = dizzy.visit(tree)
print(dm1)

dm2 = Object(
        supers=MODULE,
        locals_=(
            (('comp1',), Object(
                supers=MODULE,
                locals_=((('comp1','comp2'), Object(
                supers=COMPONENT,
                locals_=(
                    (('signal_a',), Object(
                        supers=SIGNAL,
                        locals_=()
                    )),(('signal_b',), Object(
                        supers=SIGNAL,
                        locals_=()
                    ))
                )
            )),
                    (('signal_a',), Object(
                        supers=SIGNAL,
                        locals_=()
                    )),(('signal_b',), Object(
                        supers=SIGNAL,
                        locals_=()
                    ))
                )
            )),
            (('comp1',), Object(
                supers=COMPONENT,
                locals_=(
                    (('interface1',), Object(
                        supers=INTERFACE,
                        locals_=()
                    )),(('pin1',), Object(
                        supers=PIN,
                        locals_=()
                    ))
                )
            )),
        )
)

dm3 = Link(source="signal_a", target="signal_b")
dm4 = Replace(original="signal_a", replacement="signal_b")
dm5 = Import(what="bloop", from_="blurps.ato")


# %%

# Display the tree
tree_builder = Wendy()
tree = tree_builder.build_tree(dm1)
print(tree)

# %%
