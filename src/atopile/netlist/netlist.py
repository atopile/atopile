from jinja2 import Environment, FileSystemLoader
from pathlib import Path

# Create a Jinja2 environment
this_dir = Path(__file__).parent
env = Environment(loader=FileSystemLoader(this_dir))

# Load the component template and render
comp_template = env.get_template('component_template.j2')
comps = [ {'name' : 'test1', 'value' : 1, 'fields' : { "LCSC" : "C002" , 'a field' : 'test'}}, {'name' : 'test2' , 'value' : 2, 'fields' : { "LCSC" : "C001" }} ]
components_string = comp_template.render(comps=comps)

# Load the libpart template and render
libpart_template = env.get_template('libpart_template.j2')
libparts = [ {'lib' : 'library', 'part' : 'this is a template' , 'docs' : 'this is a doc' , 'footprints' : ['footprint1', 'footprint2'] , 'fields' : { "LCSC" : "C002" , 'a field' : 'test'}, 'pins' : [{'num' : '1' , 'name' : 'p1' , 'type' : 'passive'}]} ]
libparts_string = libpart_template.render(libparts=libparts)

# Load the net template and render
net_template = env.get_template('net_template.j2')
nets = [ {'code' : '1' , 'name' : '+1V1', 'nodes' : [ {'ref' : 'C10' , 'pin' : 1, 'pinfunction' : 'does smth' , 'pintype' : 'passive'}, {'ref' : 'C8' , 'pin' : 1, 'pintype' : 'passive'}] } , {'code' : '2' , 'name' : '+2V', 'nodes' : [ {'ref' : 'C10' , 'pin' : 1, 'pintype' : 'passive'}, {'ref' : 'C8' , 'pin' : 1, 'pintype' : 'passive'}] }]
nets_string = net_template.render(nets=nets)
print(nets_string)

# Create the complete netlist
template = env.get_template('netlist_template.j2')
source = 'came from'
date = 'today'
tool = 'atopile'
netlist = template.render(source=source, date=date, tool=tool, components=components_string, libparts=libparts_string, nets=nets_string)

name = 'test'
output_file = this_dir / (name + ".net")

with output_file.open("w") as file:
    file.write(netlist)
