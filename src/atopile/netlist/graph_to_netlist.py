import igraph as ig
from atopile import model

import igraph as ig
from atopile import model

def generate_netlist_dict_from_graph(graph: ig) -> dict:
    # Generate the graph of electrical connectedness without removing other vertices
    electrial_g = graph.subgraph_edges(graph.es.select(type_eq='connects_to'), delete_vertices=False)

    # Find all the vertex indices in the main graph that are associated to a pin
    pins = graph.vs.select(type_in='pin').indices
    pin_set = set(pins)

    # Cluster the electrical graph into multiple nets
    clusters = electrial_g.connected_components(mode='weak')

    # Instantiate the net dictionary and net names
    nets = {}
    net_index = 0

    for cluster in clusters:
        cluster_set = set(cluster)

        # Intersect the pins from the main graph with the vertices in that cluster
        union_set = pin_set.intersection(cluster_set)

        if len(union_set) > 0:# If pins are found in that net
            nets[net_index] = {}

            for pin in union_set:
                pin_associated_package = model.whos_your_daddy(graph, pin)
                pin_associated_block = model.whos_your_daddy(graph, pin_associated_package.index)
                nets[net_index][pin_associated_block.index] = pin
            
            net_index += 1
            #TODO: find a better way to name nets
    
    return nets
