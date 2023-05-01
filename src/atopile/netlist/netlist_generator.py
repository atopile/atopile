from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import datetime

class KicadField:
    def __init__(self, name: str, value: str) -> None:
        self.name = name
        self.value = value

class KicadPin:
    def __init__(self, num: int, name: str, pin_type: str) -> None:
        self.num = num
        self.name = name
        self.type = pin_type

class KicadNode:
    def __init__(self, ref: str, pin: int, pin_function: str, pin_type: str) -> None:
        self.ref = ref
        self.pin = pin
        self.pin_function = pin_function
        self.pin_type = pin_type

class KicadComponent:
    def __init__(self, name, value, fields=None, lib = '', part = '', description = '', sheetpath_name = '', sheetpath_tstamp = '', tstamp = '') -> None:
        self.name = name
        self.value = value
        self.fields = fields if fields is not None else []
        self.lib = lib
        self.part = part
        self.description = description
        self.sheetpath_name = sheetpath_name
        self.sheetpath_tstamp = sheetpath_tstamp
        self.tstamp = tstamp

class KicadComponentPrototype:
    def __init__(self, lib, part, docs, footprint=None, fields=None, pins=None) -> None:
        self.lib = lib
        self.part = part
        self.docs = docs
        self.footprint = footprint if footprint is not None else []
        self.fields = fields if fields is not None else []
        self.pins = pins if pins is not None else []

class KicadNet:
    def __init__(self, code, name, nodes) -> None:
        self.code = code
        self.name = name
        self.nodes = nodes

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

class KicadNetlist:
    def __init__(self) -> None:
        self.version = 'E'
        self.source = 'unknown'
        self.date = 'unknown'
        self.tool = 'atopile'

        self.components = []
        self.component_prototypes = []
        self.nets = []

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

if __name__ == "__main__":
    a_netlist = KicadNetlist()

    test_field1 = KicadField(name='field1', value='100pF')
    test_field2 = KicadField(name='field2', value='20pF')

    test_node1 = KicadNode(ref = '1', pin = 1, pin_function = 'passive', pin_type = 'type')
    test_node2 = KicadNode(ref = '2', pin = 2, pin_function = 'passive', pin_type = 'type')

    test_pin1 = KicadPin(num = 1, name='pin1', pin_type = 'active')

    test_component = KicadComponent(name='test1', value=1, fields=[test_field1, test_field2])
    test_prototype_component = KicadComponentPrototype(lib="lib", part='this is a part', docs='this is docs', footprint=['fp1', 'fp2'], fields=[test_field1, test_field2], pins = [test_pin1])
    test_net = KicadNet(code = 1, name = '+1v1',nodes = [test_node1, test_node2])

    a_netlist.add_component_to_netlist(test_component)
    a_netlist.add_component_prototype_to_netlist(test_prototype_component)
    a_netlist.add_net_to_netlist(test_net)

    a_netlist.generate_completed_netlist()
