from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import datetime

class kicad_field:
    def __init__(self, name: str, value: str) -> None:
        self.name = name
        self.value = value

class kicad_pin:
    def __init__(self, num: int, name: str, pin_type: str) -> None:
        self.num = num
        self.name = name
        self.type = pin_type

class kicad_node:
    def __init__(self, ref: str, pin: int, pin_function: str, pin_type: str) -> None:
        self.ref = ref
        self.pin = pin
        self.pin_function = pin_function
        self.pin_type = pin_type

class kicad_netlist:
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

    def add_component_to_netlist(self, name: str, value: str, fields: list) -> None:
        fields_dict = {}
        for field in fields:
            fields_dict[field.name] = field.value

        self.components.append({'name' : name, 'value' : value, 'fields' : fields_dict})
    
    def add_component_prototype_to_netlist(self, lib: str, part: str, docs: str, footprint: list, fields: list, pins: list) -> None:
        pin_list = []
        for pin in pins:
            pin_dict = {}
            pin_dict['num'] = pin.num
            pin_dict['name'] = pin.name
            pin_dict['pin_type'] = pin.type
            
            pin_list.append(pin_dict)
        
        fields_dict = {}
        for field in fields:
            fields_dict[field.name] = field.value

        self.component_prototypes.append({'lib' : lib, 'part' : part, 'docs' : docs, 'footprints' : footprint, 'fields' : fields_dict, 'pins' : pin_list})

    def add_net_to_netlist(self, code: int, name: str, nodes: list) -> None:
        node_list = []
        for node in nodes:
            node_dict = {}
            node_dict['ref'] = node.ref
            node_dict['pin'] = node.pin
            node_dict['pinfunction'] = node.pin_function
            node_dict['pintype'] = node.pin_type
            
            node_list.append(node_dict)
        
        self.nets.append({'code' : code, 'name' : name, 'nodes' : node_list})

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

a_netlist = kicad_netlist()

test_field1 = kicad_field(name='field1', value='100pF')
test_field2 = kicad_field(name='field2', value='20pF')
print(test_field1.name)

test_node1 = kicad_node(ref = '1', pin = 1, pin_function = 'passive', pin_type = 'type')
test_node2 = kicad_node(ref = '2', pin = 2, pin_function = 'passive', pin_type = 'type')

test_pin1 = kicad_pin(num = 1, name='pin1', pin_type = 'active')

a_netlist.add_component_to_netlist(name='test1', value=1, fields=[test_field1, test_field2])
a_netlist.add_component_prototype_to_netlist(lib="lib", part='this is a part', docs='this is docs', footprint=['fp1', 'fp2'], fields=[test_field1, test_field2], pins = [test_pin1])
a_netlist.add_net_to_netlist(code = 1, name = '+1v1',nodes = [test_node1, test_node2])
a_netlist.generate_completed_netlist()

# comps = [ {'name' : 'test1', 'value' : 1, 'fields' : { "LCSC" : "C002" , 'a field' : 'test'}}, {'name' : 'test2' , 'value' : 2, 'fields' : { "LCSC" : "C001" }} ]
# components_string = comp_template.render(comps=comps)

# # Load the libpart template and render
# libpart_template = env.get_template('libpart_template.j2')
# libparts = [ {'lib' : 'library', 'part' : 'this is a template' , 'docs' : 'this is a doc' , 'footprints' : ['footprint1', 'footprint2'] , 'fields' : { "LCSC" : "C002" , 'a field' : 'test'}, 'pins' : [{'num' : '1' , 'name' : 'p1' , 'type' : 'passive'}]} ]
# libparts_string = libpart_template.render(libparts=libparts)

# # Load the net template and render
# net_template = env.get_template('net_template.j2')
# nets = [ {'code' : '1' , 'name' : '+1V1', 'nodes' : [ {'ref' : 'C10' , 'pin' : 1, 'pinfunction' : 'does smth' , 'pintype' : 'passive'}, {'ref' : 'C8' , 'pin' : 1, 'pintype' : 'passive'}] } , {'code' : '2' , 'name' : '+2V', 'nodes' : [ {'ref' : 'C10' , 'pin' : 1, 'pintype' : 'passive'}, {'ref' : 'C8' , 'pin' : 1, 'pintype' : 'passive'}] }]
# nets_string = net_template.render(nets=nets)