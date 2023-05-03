# %%
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import datetime
from typing import Optional
from attrs import define, field

from atopile.model.model import (
    Graph,
    VertexType,
    generate_uid_from_path,
)

import atopile.netlist.graph_data_extraction as graph_data_extract

@define
class KicadField:
    name: str
    value: str

@define
class KicadPin:
    # def __init__(self, num: int, name: str, pin_type: str) -> None:
    num: str
    name: str
    pin_type: str = ''

@define
class KicadNode:
    # def __init__(self, ref: str, pin: int, pin_function: Optional[str] = None, pin_type: str) -> None:
    ref: str
    pin: int
    pin_function: str = ''
    pin_type: str = ''

@define
class KicadComponent:
    # def __init__(self, name, value, fields=None, lib = '', part = '', description = '', sheetpath_name = '', sheetpath_tstamp = '', tstamp = '') -> None:
    name: str
    value: str
    fields: list = field(factory=list)
    lib: str = ''
    part: str = ''
    description: str = ''
    sheetpath_name: str = ''
    sheetpath_tstamp: str = ''
    tstamp: str = ''

@define
class KicadComponentPrototype:
    #def __init__(self, lib, part, docs, footprint=None, fields=None, pins=None) -> None:
    lib: str
    part: str
    docs: str
    footprint: list = field(factory=list)
    fields: list = field(factory=list)
    pins: list = field(factory=list)

    def add_pin(self, pin = KicadPin):
        self.pins.append(pin)

@define
class KicadNet:
    # def __init__(self, code, name, nodes) -> None:
    code: str
    name: str
    nodes: list = field(factory=list)

    def add_node_to_net(self, node: KicadNode) -> None:
        self.nodes.append(node)

# Deprecated -- I don't think these are used
# def add_field(object, field: KicadField) -> None:
#     if hasattr(object, 'fields'):
#         object.fields.append(field)
#     else:
#         print('error')

# def add_node(object, field: KicadNode) -> None:
#     if hasattr(object, 'nodes'):
#         object.nodes.append(field)
#     else:
#         print('error')

@define
class KicadNetlist:
    version: str = 'E'
    source: str ='unknown'
    date: str = 'unknown'
    tool: str = 'atopile'
    
    components: list = field(factory=list)
    component_prototypes: list = field(factory=list)
    nets: list = field(factory=list)
    
    def add_metadata_to_netlist(self, source: str, tool: str, version = 'E') -> None:
        now = datetime.datetime.now()

        self.version = version
        self.source = source
        self.date = now
        self.tool = tool

    def add_component_to_netlist(self, component: KicadComponent) -> None:

        self.components.append(component)

    def add_component_prototype_to_netlist(self, component_prototype: KicadComponentPrototype) -> None:

        self.component_prototypes.append(component_prototype)

    def add_net_to_netlist(self, net: KicadNet) -> None:

        self.nets.append(net)

    def generate_completed_netlist(self) -> None:
        # Create a Jinja2 environment
        this_dir = Path(__file__).parent
        env = Environment(loader=FileSystemLoader(this_dir))

        # Load the component template and render
        comp_template = env.get_template('component_template.j2')
        components_string = comp_template.render(comps = self.components)

        # Load the libpart template and render
        libpart_template = env.get_template('libpart_template.j2')
        libparts_string = libpart_template.render(libparts = self.component_prototypes)

        # Load the net template and render
        net_template = env.get_template('net_template.j2')
        nets_string = net_template.render(nets = self.nets)

        # Create the complete netlist
        source = self.source
        date = self.date
        tool = self.tool
        template = env.get_template('netlist_template.j2')
        netlist = template.render(source=source, date=date, tool=tool, components=components_string, libparts=libparts_string, nets=nets_string)

        name = 'test'
        output_file = this_dir / (name + ".net")

        with output_file.open("w") as file:
            file.write(netlist)


def generate_nets_dict_from_graph(g: Graph, netlist: KicadNetlist, root_index: Optional[int] = 0) -> dict:
    instance_graph = Graph()
    electrical_graph = Graph()
    instance_graph.graph = g.get_sub_part_of_graph(root_vertex = 0)

    # Extract the electrical graph from the instance subgraph
    electrical_graph.graph = instance_graph.graph.subgraph_edges(instance_graph.graph.es.select(type_eq='connects_to'), delete_vertices=False)

    # Find all the vertex indices in the main graph that are associated to a pin
    pins = electrical_graph.graph.vs.select(type_in='pin').indices
    pin_set = set(pins)

    # Extract all the clusters. The ones that contain pins are considered nets.
    clusters = electrical_graph.graph.connected_components(mode='weak')

    # Instantiate the net dictionary and net index
    nets = {}
    net_index = 0

    for cluster in clusters:
        cluster_set = set(cluster)

        # Intersect the pins from the main graph with the vertices in that cluster
        union_set = pin_set.intersection(cluster_set)

        if len(union_set) > 0: # If pins are found in that net
            net = KicadNet(code=net_index, name=net_index)
            # Create a new dict entry
            nets[net_index] = {}

            for pin in union_set:
                vertex_path = electrical_graph.get_vertex_path(pin)
                parent_path = graph_data_extract.get_parent_from_path(vertex_path)
                pin_number = electrical_graph.get_vertex_ref(pin)
                node = KicadNode(ref=parent_path, pin=pin_number)
                net.add_node_to_net(node)
                nets[net_index][parent_path] = electrical_graph.get_vertex_ref(pin)

            netlist.add_net_to_netlist(net)
            net_index += 1
            #TODO: find a better way to name nets

    return nets

def generate_component_list_from_graph(g: Graph, netlist: KicadNetlist, root_index = 0):
    instance_graph = Graph()
    instance_graph.graph = g.get_sub_part_of_graph(root_vertex = 0)

    # find all the packages within that graph
    packages = graph_data_extract.get_packages(instance_graph.graph)

    for package in packages:
        # Find the parent block
        parent_block = graph_data_extract.get_block_from_package(g, package)

        name = graph_data_extract.get_vertex_parameter(parent_block, "path") 
        uid = graph_data_extract.get_vertex_parameter(parent_block, "uid")
        lib = graph_data_extract.get_vertex_parameter(parent_block, "lib")
        lib_part = graph_data_extract.get_vertex_parameter(parent_block, "lib_part")
        value = graph_data_extract.get_vertex_parameter(parent_block, "value")
        description = graph_data_extract.get_vertex_parameter(parent_block, "description")
        footprint = graph_data_extract.get_vertex_parameter(package, "footprint")

        component = KicadComponent(name=name,value=value,lib=lib,part=lib_part,description=description,tstamp=uid)
        netlist.add_component_to_netlist(component)

def generate_comp_proto_list_from_graph(g: Graph, netlist: KicadNetlist, root_index = 0):
    comp_proto_packages = graph_data_extract.get_package_instances_of_seed(g, root_index)

    for package in comp_proto_packages:

        parent_block = graph_data_extract.get_block_from_package(g, package)

        name = graph_data_extract.get_vertex_parameter(parent_block, "path")
        lib = graph_data_extract.get_vertex_parameter(parent_block, "lib")
        lib_part = graph_data_extract.get_vertex_parameter(parent_block, "lib_part")
        description = graph_data_extract.get_vertex_parameter(parent_block, "description")
        footprint = graph_data_extract.get_vertex_parameter(package, "footprint")
        
        component_proto = KicadComponentPrototype(lib = lib, part = lib_part, docs = description)
        
        pins = graph_data_extract.get_pin_list_from_package(g, package)
        for pin in pins:
            pin_num = graph_data_extract.get_vertex_parameter(pin, "ref")
            pin_name = graph_data_extract.get_vertex_parameter(pin, "ref")
            netlist_pin = KicadPin(num = pin_num, name = pin_name)

            component_proto.add_pin(netlist_pin)
        
        netlist.add_component_prototype_to_netlist(component_proto)



# %%
if __name__ == "__main__":
    a_netlist = KicadNetlist()

    test_field1 = KicadField(name='field1', value='100pF')
    test_field2 = KicadField(name='field2', value='20pF')

    test_node1 = KicadNode(ref = '1', pin = 1, pin_function = 'passive', pin_type = 'type')
    test_node2 = KicadNode(ref = '2', pin = 2, pin_function = 'passive', pin_type = 'type')

    test_pin1 = KicadPin(num = 1, name='pin1', pin_type = 'active')

    test_component = KicadComponent(name='test1', value=1)#, fields=[test_field1, test_field2])
    test_prototype_component = KicadComponentPrototype(lib="lib", part='this is a part', docs='this is docs', footprint=['fp1', 'fp2'], fields=[test_field1, test_field2], pins = [test_pin1])
    test_net = KicadNet(code = 1, name = '+1v1',nodes = [test_node1, test_node2])

    a_netlist.add_component_to_netlist(test_component)
    a_netlist.add_component_prototype_to_netlist(test_prototype_component)
    a_netlist.add_net_to_netlist(test_net)

    a_netlist.generate_completed_netlist()