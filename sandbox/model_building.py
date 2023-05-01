import igraph as ig
from atopile.model.model import (
    Graph,
    VertexType,
    generate_uid_from_path,
    get_parent_from_path,
    get_vertex_path,
    get_vertex_ref,
)

#%%
"""
The code below is equivalent to:

resistor.ato

def seed:
    symbol = None
    def package:
        package = None
        def pin:
            pass
    def ethereal_pin:
        pass

from ... import 0402

block resistor():
    package:
        actual_package: 0402 / &small_res
        pin 1
        pin 2

    package res_package;
    signal vcc ~ 1
    signal gnd ~ 2


def vdiv:
    vdiv_res_1 = resistor()
    vdiv_res_2 = resistor()

    INPUT = ethereal_pin()
    OUTPUT = ethereal_pin()
    GROUND = ethereal_pin()

    INPUT ~ vdiv_res_1[0]
    OUTPUT ~ vdiv_res_1[1]
    GROUND ~ vdiv_res_2[1]
    vdiv_res_1[1] ~ vdiv_res_2[0]

a_voltage_divider = vdiv()
"""
seed_graph = Graph()
g = Graph()

# Define the graph seed. The seed represents a prototype of the data structure.
# The seed is explicit for now but will ultimately live within the compiler.
g.add_vertex("resistor.ato", VertexType.block)
g.add_vertex("seed", VertexType.block, defined_by="resistor.ato")
g.add_vertex_parameter("resistor.ato/seed", "uid")
g.add_vertex_parameter("resistor.ato/seed", "lib")
g.add_vertex_parameter("resistor.ato/seed", "lib_part")
g.add_vertex_parameter("resistor.ato/seed", "value")
g.add_vertex_parameter("resistor.ato/seed", "description")
# g.add_vertex("block", VertexType.block, defined_by="resistor.ato/seed")
g.add_vertex("package", VertexType.package, defined_by="resistor.ato/seed")
g.add_vertex_parameter("resistor.ato/seed/package", "footprint")
g.add_vertex("ethereal_pin", VertexType.ethereal_pin, defined_by="resistor.ato/seed")
g.add_vertex("pin", VertexType.pin, defined_by="resistor.ato/seed/package")

# Define a resistor prototype
g.create_instance("resistor.ato/seed", "resistor", defined_by="resistor.ato")
g.set_vertex_parameter("resistor.ato/resistor", "uid", generate_uid_from_path("resistor.ato/resistor"))
g.set_vertex_parameter("resistor.ato/resistor", "lib", "Device")
g.set_vertex_parameter("resistor.ato/resistor", "lib_part", "R_Small")
g.set_vertex_parameter("resistor.ato/resistor", "description", "Current can flow here if traded against voltage")
g.create_instance("resistor.ato/resistor/package", "resistor_package", part_of="resistor.ato/resistor")
g.set_vertex_parameter("resistor.ato/resistor/resistor_package", "footprint", "0402")
g.create_instance("resistor.ato/resistor/ethereal_pin", "1", part_of="resistor.ato/resistor")
g.create_instance("resistor.ato/resistor/ethereal_pin", "2", part_of="resistor.ato/resistor")
g.create_instance("resistor.ato/resistor/resistor_package/pin", "1", part_of="resistor.ato/resistor/resistor_package")
g.create_instance("resistor.ato/resistor/resistor_package/pin", "2", part_of="resistor.ato/resistor/resistor_package")
g.add_connection("resistor.ato/resistor/1", "resistor.ato/resistor/resistor_package/1")
g.add_connection("resistor.ato/resistor/2", "resistor.ato/resistor/resistor_package/2")

g.create_instance("resistor.ato/seed", "vdiv", defined_by="resistor.ato")
g.create_instance("resistor.ato/resistor", "vdiv_res_1", part_of="resistor.ato/vdiv")
g.set_vertex_parameter("resistor.ato/vdiv/vdiv_res_1", "value", "1k")
g.create_instance("resistor.ato/resistor", "vdiv_res_2", part_of="resistor.ato/vdiv")
g.set_vertex_parameter("resistor.ato/vdiv/vdiv_res_2", "value", "2k")
g.create_instance("resistor.ato/vdiv/ethereal_pin", "INPUT", part_of="resistor.ato/vdiv")
g.create_instance("resistor.ato/vdiv/ethereal_pin", "OUTPUT", part_of="resistor.ato/vdiv")
g.create_instance("resistor.ato/vdiv/ethereal_pin", "GROUND", part_of="resistor.ato/vdiv")
# Creating a random pin just to see if it shows up in the netlist (it should)
# Note that pins are always dependent on packages, so connecting a pin as part_of a block should usually not be allowed
g.create_instance("resistor.ato/vdiv/package/pin", "1", part_of="resistor.ato/vdiv")

g.add_connection("resistor.ato/vdiv/INPUT", "resistor.ato/vdiv/vdiv_res_1/1")
g.add_connection("resistor.ato/vdiv/OUTPUT", "resistor.ato/vdiv/vdiv_res_1/2")
g.add_connection("resistor.ato/vdiv/GROUND", "resistor.ato/vdiv/vdiv_res_2/2")
g.add_connection("resistor.ato/vdiv/vdiv_res_1/2", "resistor.ato/vdiv/vdiv_res_2/1")

g.create_instance("resistor.ato/vdiv", "a_voltage_divider", part_of="resistor.ato")

g.plot(debug=True)

#%%
def generate_nets_dict_from_graph(g: Graph, root_index: int) -> dict:
    entry = g.graph
    # Generate the part_of connectedness graph without removing other vertices
    part_of_g = g.graph.subgraph_edges(entry.es.select(type_eq='part_of'), delete_vertices=False)
    # The delete vertices is required because the subgraph built below depends on the vertex indices

    # Select only the subgraph that contains the root
    instance_graph = part_of_g.subcomponent(root_index)

    # This subgraph contain the part_of connectedness tree that contains the root vertex
    # and that also has electical connections within that tree
    subgraph = entry.induced_subgraph(instance_graph)

    # Extract the electrical graph from the instance subgraph
    electrical_g = subgraph.subgraph_edges(subgraph.es.select(type_eq='connects_to'), delete_vertices=False)

    # Find all the vertex indices in the main graph that are associated to a pin
    pins = electrical_g.vs.select(type_in='pin').indices
    pin_set = set(pins)

    # Extract all the clusters. The ones that contain pins are considered nets.
    clusters = electrical_g.connected_components(mode='weak')

    # Instantiate the net dictionary and net index
    nets = {}
    net_index = 0

    for cluster in clusters:
        cluster_set = set(cluster)

        # Intersect the pins from the main graph with the vertices in that cluster
        union_set = pin_set.intersection(cluster_set)

        if len(union_set) > 0: # If pins are found in that net
            # Create a new dict entry
            nets[net_index] = {}

            for pin in union_set:
                vertex_path = get_vertex_path(electrical_g, pin)
                parent_path = get_parent_from_path(vertex_path)
                nets[net_index][parent_path] = get_vertex_ref(electrical_g, pin)

            net_index += 1
            #TODO: find a better way to name nets

    return nets

import atopile.netlist.netlist_generator as nlg


def generate_component_list_from_graph(graph: ig, netlist: nlg.KicadNetlist):
    # Select the component block in the graph


    # Tim; I wasn't able to find what model was supposed to reference in the original file, so I couldn't import it over here.

    component_blocks = model.find_blocks_associated_to_package(graph)

    component_block_indices = model.get_vertex_index(component_blocks)
    #TODO: make sure that I'm only getting child blocks and not parents

    components = []

    for comp_block_index in component_block_indices:
        block_path = model.get_vertex_path(graph, comp_block_index)
        print(block_path)
        components.append(model.generate_uid_from_path(block_path))

    return components

print(generate_nets_dict_from_graph(g, 0))

print('parameter: ', g.graph.vs.find(path_eq="resistor.ato/resistor/resistor_package")["footprint"])
print('uid', g.graph.vs.find(path_eq="resistor.ato/resistor")["uid"])

netlist = nlg.KicadNetlist()

generate_component_list_from_graph(g, netlist)

# %%


a = 0

def something(b):
    return a + b
# %%
