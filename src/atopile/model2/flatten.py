"""
Find import references.
"""
from typing import Optional

from . import datamodel as dm1
from .datamodel_flat import Instance, Link
from .datatypes import Ref


def get_ref_from_instance(ref: Ref, instance: Instance) -> Instance:
    """Get a ref from an instance."""
    for ref_part in ref:
        instance = instance.children[ref_part]
    return instance


def build(obj: dm1.Object) -> Instance:
    """Build a flat datamodel."""
    return _build((), obj)


def _build(addr: Ref, obj: dm1.Object, instance: Optional[Instance] = None) -> Instance:
    """Visit an object."""
    if instance and obj in instance.origin.supers_bfs:
        return instance
    elif obj.supers_bfs:
        instance = _build(addr, obj.supers_bfs[0], instance)
    else:
        instance = Instance(addr=addr)

    instance.origin = obj

    # visit all the child objects
    child_objects = obj.locals_by_type[dm1.Object]
    instance.children_from_classes.update(
        {ref[0]: _build(addr + ref, value) for ref, value in child_objects}
    )

    # visit replacements after the children are created
    replacements = obj.locals_by_type[dm1.Replace]
    for _, replace in sorted(replacements, key=lambda x: len(x[1].original_ref)):
        assert isinstance(replace, dm1.Replace)
        instance_to_replace = get_ref_from_instance(replace.original_ref, instance)
        _build(
            instance_to_replace.addr,
            replace.replacement_obj,
            instance_to_replace
        )

    # visit all the child params
    params = obj.locals_by_type[(str, int)]
    for ref, value in params:
        to_mod = get_ref_from_instance(ref[:-1], instance)
        to_mod.children[ref[-1]] = value

    # visit all the child links
    links = obj.locals_by_type[dm1.Link]
    for _, link in links:
        assert isinstance(link, dm1.Link)
        source_instance = get_ref_from_instance(link.source_ref, instance)
        target_instance = get_ref_from_instance(link.target_ref, instance)

        flat_link = Link(link, instance, source_instance, target_instance)

        source_instance.linked_to_me.append(flat_link)
        target_instance.linked_to_me.append(flat_link)
        instance.links.append(flat_link)

    return instance
