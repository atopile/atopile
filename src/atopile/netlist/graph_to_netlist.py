import igraph as ig
from atopile import model

def generate_netlist_dict_from_graph(graph: ig) -> dict:
    # Generate the graph of electrical connectedness without removing other vertices
    electrial_g = graph.subgraph_edges(graph.es.select(type_eq='connects_to'), delete_vertices=False)

    # Find all the pin indices in the main graph
    pins = graph.vs.select(type_in='pin').indices
    pin_set = set(pins)

    # Find the nets in that graph
    clusters = electrial_g.connected_components(mode='weak')

    # Instantiate the net dictionary and net names
    nets = {}
    net_index = 0

    for cluster in clusters:
        cluster_set = set(cluster)

        # Intersect the electrical pins and the pins in the current cluster
        union_set = pin_set.intersection(cluster_set)

        if len(union_set) > 0:
            nets[net_index] = {}
            for pin in union_set:
                pin_associated_package = model.whos_your_daddy(graph, pin)
                pin_associated_block = model.whos_your_daddy(graph, pin_associated_package.index)
                nets[net_index][pin_associated_block.index] = pin
            net_index += 1
    
    return nets
