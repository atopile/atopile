import hashlib
import uuid
import igraph as ig

def generate_uid_from_path(path: str) -> str:
    path_as_bytes = path.encode('utf-8')
    hashed_path = hashlib.blake2b(path_as_bytes, digest_size=16).digest()
    return uuid.UUID(bytes=hashed_path)


VERTEX_COLOR_DICT = {
    "file": "red",
    "module": "green",
    "component": "cyan",
    "feature": "magenta",
    "pin": "yellow",
    "signal": "pink",
}

EDGE_COLOR_DICT = {
    "connects_to": "blue",
    "part_of": "black",
    "instance_of": "red",
    "inherits_from": "green",
}

def plot(graph, *args, debug=False, **kwargs):
    assert all(t is not None for t in graph.vs["type"])

    kwargs["vertex_color"] = [VERTEX_COLOR_DICT.get(type_name, "grey") for type_name in graph.vs["type"]]
    kwargs["edge_color"] = [EDGE_COLOR_DICT.get(type_name, "grey") for type_name in graph.es["type"]]
    kwargs["vertex_label_size"] = 8
    kwargs["edge_label_size"] = 8
    if debug:
        kwargs["vertex_label"] = [f"{i}: {vs['path']}" for i, vs in enumerate(graph.vs)]
        kwargs["edge_label"] = graph.es["type"]
    else:
        kwargs["vertex_label"] = graph.vs["ref"]
    return ig.plot(graph, *args, **kwargs)
