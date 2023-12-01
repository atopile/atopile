"""
Pipe that takes in a list of instances and gives them a designator.
- Iterates over the list once to find lock file names
   - adds lock file names to a set (prefix + integer)
   - gives each instance a designator from the lock file names
- Iterates over the list again to find the designators for unnamed instances
    - For each prefix, increment the integer until it is not in the set
    - A counter is used to keep track of the integer
"""
from typing import Any, Iterable, Mapping, Optional, Type

from .datamodel import Instance
from .instance_methods import match_components, dfs


def make_designators(root: Instance) -> Instance:
    """Make designators for instances."""

    # add a filter to the input to only accept components
    instances = list(filter(match_components, dfs(root)))


    used_names = set()
    unnamed_instances = []

    # Iterate over all instances
    for instance in instances:
        # Check if the instance already has a designator
        designator = instance.children.get("designator", None)
        if designator is not None:
            used_names.add(designator)
        else:
            unnamed_instances.append(instance)

    # Give each unnamed instance a designator
    for instance in unnamed_instances:
        prefix = get_prefix(instance)
        designator = get_designator(prefix, used_names)  # Assuming "prefix" is a valid prefix
        used_names.add(designator)
        instance.children["designator"] = designator

    return root

def get_designator(prefix: str, used_names: set[str]) -> str:
    """Get a designator."""
    i = 1
    while True:
        name = f"{prefix}{i}"
        if name not in used_names:
            return name
        i += 1

def get_prefix(instance: Instance) -> str:
    """Get the prefix of an instance."""
    return instance.children.get("designator_prefix", "U")

# first attempt
# 1.55 ms ± 27.7 µs per loop (mean ± std. dev. of 7 runs, 1,000 loops each)