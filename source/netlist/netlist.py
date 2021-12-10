import networkx as nx

# 0. netlist = graph

#TODO add name precendence
# t1 is basically a reduced version of the grap
# t1_netlist = [
#     {name, value, properties, real,
#       neighbors={pin: [{&vertex, pin}]},
# ]


# t2 is transposed to list nets instead of vertices
# t2_netlist = [(properties, vertices=[comp=(name, value, properties), pin)])]

def make_t2_netlist_from_t1(netlist):

    #TODO

    # make undirected graph where nodes=(vertex, pin),
    #   edges=in neighbors relation
    # nets = connected components
    # opt: determine net.prop.name by nodes?

    #TODO remove dep or put into readme

    class vertex():
        def __init__(self, node, pin):
            self.node = node
            self.pin = pin

        def __hash__(self):
            val =  hash(hash(self.node["name"])+hash(self.pin))
            #print("Hash {}: {}".format(repr(self), val))
            return val

        def __repr__(self):
            return "vertex({},{})".format(
                self.node.get("name"),
                self.pin
            )

        def __eq__(self, other):
            return hash(self) == hash(other)


    #print(netlist)
    G = nx.Graph()
    edges = [((vertex(node, spin)),
                (vertex(neighbor["vertex"], neighbor["pin"])))
        for node in netlist
        for spin,v_neighbors in node.get("neighbors", {1: []}).items()
        for neighbor in v_neighbors
    ]
    G.add_edges_from(edges)
    #print("\nEdges", edges)
    #print("\nHashedEdges", list(map(lambda x: tuple(map(hash, x)), edges)))
    #print("\nGraphEdges", list(G.nodes))

    nets = list(nx.connected_components(G))
    #print("\nnets", nets)

    t2_netlist = [
        {
            #TODO use name precedence instead
            "properties": {
                "name": "-".join([vertex.node["name"] for vertex in net if not vertex.node["real"]]),
            },
            "vertices": [
                {
                    "comp": {k:v for k,v in vertex.node.items() if k not in ["real", "neighbors"]},
                    "pin": vertex.pin
                }
                for vertex in net
                if vertex.node["real"]
            ]
        }
        for net in nets
    ]

    #print("\nT2", t2_netlist)


    #import matplotlib.pyplot as plt
    #nodes = [vertex(node, spin)
    #    for node in netlist
    #    for spin in node.get("neighbors", {1: None}).keys()
    #]
    #nodes_dict = {node:"{}:{}".format(node.node["name"], node.pin)
    #    for node in nodes}
    #plot = plt.subplot(121)
    #layout = nx.spring_layout(G)
    #nx.draw(G, pos=layout)
    #nx.draw_networkx_labels(G, pos=layout, labels=nodes_dict)
    #plt.show()

    return t2_netlist