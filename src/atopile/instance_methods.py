

#######

# For Tim



def get_children(address: str) -> Iterable[Instance]:
    root_addr = get_entry(address)
    root_instance = lofty[root_addr]
    ref_str = get_ref(address)
    for child_ref in ref_str:
        nested_instance = root_instance.children[child_ref]
    children_to_return = {}
    for child_key, child_to_return in nested_instance.children.items():
        children_to_return[address + child_key] = child_to_return #TODO: might want to add a function to append two strings together

    return children_to_return



