import os
import yaml
import string

class component:
    def __init__(self) -> None:
        self.value = None
        self.characteristics = None
        self.description = str
        self.library = {}
        self.sheetpath = {}
        self.tstamp = None # probably have to delete this since it will be the uuid

class netlist:
    def __init__(self) -> None:
        self.version = "E"
        self.date = None
        self.tool = 'atopile'
        self.sheets = {} # format uuid : sheet info
        self.components = {} # format uuid : comp info 
        self.nets = {}
        self.netlist_data = {"version" : "completed"}


    def populate_netlist(self, data) -> None:
        def string_constructor(loader, node):
 
            t = string.Template(node.value)
            value = t.substitute(data)
            return value
 
        loader = yaml.SafeLoader
        loader.add_constructor('tag:yaml.org,2002:str', string_constructor)
    
        token_re = string.Template.pattern
        loader.add_implicit_resolver('tag:yaml.org,2002:str', token_re, None)
        
        with open('netlist_proto.yaml', 'r') as f:
            netlist_proto = f.read()
            
        completed_netlist = yaml.load(netlist_proto, Loader=loader)
        
        return completed_netlist
        
    
    def generate_netlist(self, name = str) -> None:
        # Create a build directory
        if not os.path.exists('../../build'):
            os.makedirs('../../build')
        
        # generate the netlist or clean the previous version from build dir
        output_loc = "../../build/" + name + ".yaml"
        with open(output_loc, "w") as file:
            file.write("")
        
        output_netlist = self.populate_netlist(self.netlist_data)
        output_file = yaml.dump(output_netlist, sort_keys = False)

        with open(output_loc, "a") as file:
            file.write(output_file)

    
net = netlist()
net.generate_netlist(name = 'export')