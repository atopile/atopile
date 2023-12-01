from typing import Any, Iterable, Mapping, Optional, Type

from .datamodel import Instance
from .instance_methods import match_components, dfs


def make_designators(root: Instance) -> Instance:
    """Assign designators to all components."""
    instances = list(filter(match_components, dfs(root)))

    used_names = set()
    unnamed_instances = []

    # First pass to find used designators
    for instance in instances:
        designator = instance.children.get("designator", None)
        if designator is not None:
            used_names.add(designator)
        else:
            unnamed_instances.append(instance)

    # Assign designators to unnamed instances
    for instance in unnamed_instances:
        prefix = instance.children.get("designator_prefix", "U")
        i = 1
        while f"{prefix}{i}" in used_names:
            i += 1
        new_designator = f"{prefix}{i}"
        used_names.add(new_designator)
        instance.children["designator"] = new_designator

    return root

# first attempt
# 1.55 ms ± 27.7 µs per loop (mean ± std. dev. of 7 runs, 1,000 loops each)