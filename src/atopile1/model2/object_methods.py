import functools
from typing import Iterable, Iterator, Mapping
import collections

from atopile.model2 import errors
from atopile.model2.datamodel import Object, Import, BUILTINS
from atopile.model2.datatypes import Ref
from atopile.model2.generic_methods import closest_common


def iter_supers(obj: Object) -> Iterator[Object]:
    """Iterate over all the supers of an instance."""
    while obj.all_supers is not None:
        obj = obj.all_supers[0]
        yield obj


def lowest_common_super(objects: Iterable[Object], include_self: bool = True) -> Object:
    """
    Return the lowest common parent of a set of instances.
    """
    __iter_supers = functools.partial(iter_supers)
    return closest_common(map(__iter_supers, objects), get_key=id)


def lookup_obj_in_obj(start: Object, ref: Ref) -> Object:
    """
    This method finds an object with a given ref in another object.
    By asserting that the final object is a another object, we can operate
    faster than if we were searching for an unknown type.
    """
    assert isinstance(start, Object)
    name = ref[0]

    try:
        obj = start.objs[name]
    except KeyError:
        raise errors.AtoKeyError.from_ctx(
            f"Name '{name}' not found in '{start}'.",
            start.src_ctx
        ) from KeyError

    # if the length was 1, we've found the object we're looking for
    if len(ref) == 1:
        return obj

    # otherwise, we need to keep looking
    return lookup_obj_in_obj(obj, ref[1:])


def lookup_obj_in_closure(closure: tuple[Object], ref: Ref) -> Object:
    """
    This method finds an object in the closure of another object, traversing import statements.
    """
    for scope in closure:

        obj_lead = scope.objs.get(ref[0])
        import_leads = {
            imp_ref: imp for imp_ref, imp in scope.imports.items() if ref[0] == imp_ref[0]
        }

        if import_leads and obj_lead:
            # TODO: improve error message with details about what items are conflicting
            raise errors.AtoAmbiguousReferenceError.from_ctx(
                f"Name '{ref[0]}' is ambiguous in '{scope}'.",
                scope.src_ctx
            )

        if obj_lead is not None:
            return lookup_obj_in_obj(obj_lead, ref[1:])

        if import_leads:
            for ref_len in range(len(ref), 0, -1):
                trimmed_ref = ref[:ref_len]
                if trimmed_ref in import_leads:
                    remaining_ref = ref[ref_len:]
                    if remaining_ref:
                        return lookup_obj_in_obj(
                            import_leads[trimmed_ref].what_obj,
                            remaining_ref
                        )
                    return import_leads[trimmed_ref].what_obj

    if ref in BUILTINS:
        return BUILTINS[ref]

    raise KeyError(ref)
