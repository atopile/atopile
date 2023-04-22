import igraph as ig

def plot(g: ig.Graph, *args, **kwargs):
    color_dict = {
        "block": "red",
        "package": "green",
        "pin": "cyan",
        "ethereal_pin": "magenta",
        "connects_to": "blue",
        "part_of": "black",
    }
    try:
        g.vs["type"]
    except KeyError as ex:
        raise KeyError("Graph is missing a 'type' vertex attribute. Is there enough data in this graph") from ex

    kwargs["vertex_color"] = [color_dict.get(type_name, "grey") for type_name in g.vs["type"]]
    kwargs["vertex_label"] = g.vs["ref"]
    kwargs["edge_color"] = [color_dict[type_name] for type_name in g.es["type"]]
    return ig.plot(g, *args, **kwargs)
