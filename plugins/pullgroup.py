import csv
import os
from pcbnew import *

def parse_hierarchy(csv_file) -> dict:
    hierarchy_dict = {}

    with open(csv_file, mode='r', newline='') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header row if present

        for row in reader:
            # Extract name and designator
            package, package_instance, name, designator = row

            # Check if top level exists in dict
            if package_instance not in hierarchy_dict:
                hierarchy_dict[package_instance] = {}
                hierarchy_dict[package_instance]['_package'] = package

            # Add the designator and full name as a key-value pair
            hierarchy_dict[package_instance][designator] = name

    return hierarchy_dict

def name2des(name: str,input_dict: dict):
    for key, value in input_dict.items():
        if value == name:
            return key
    return None


class PullGroup(ActionPlugin):
    def defaults(self):
        self.name = "Pull Group"
        self.category = "Pull Group Layout Atopile"
        self.description = "Layout components on PCB in same spatial relationships as components on schematic"
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), 'download.png') # Optional, defaults to ""

    def Run(self):
        board: BOARD = GetBoard()
        fn = board.GetFileName()
        prjpatha = fn.split('/')
        prjpath = '/'.join(prjpatha[:prjpatha.index('elec')])
        csv_file_path = '/'.join([prjpath,'build','default','group_map.csv'])
        heir = parse_hierarchy(csv_file_path)

        # Setup groups if first time opening
        init_gs = board.Groups()
        init_g_names = list(g.GetName() for g in init_gs)

        for k in heir.keys():
            index = -1
            try:
                index = init_g_names.index(k)
                g = init_gs[index]
            except ValueError:
                index = -1
                g = PCB_GROUP(board)
                g.SetName(k)
                board.Add(g)
            
            # Populate group with footprints
            for ref in heir.get(k,{}).keys():
                if ref:
                    fp = board.FindFootprintByReference(ref)
                    if fp:
                        g.AddItem(fp)

        # Pull Selected Groups
        sel_gs = [g for g in board.Groups() if g.IsSelected()] #selected groups
        
        for sg in sel_gs:
            g_name = sg.GetName()
            try:
                with open('/'.join([prjpath,'.ato','modules',heir[g_name]['_package'],'elec','layout','layout.csv']), mode='r', newline='') as file:
                    pass
                    reader = csv.reader(file)
                    next(reader)  # Skip header row if present

                    for row in reader:
                        # Extract name and designator
                        name,x,y,theta = row
                        des = name2des(name,heir[g_name])
                        if des:
                            fp: FOOTPRINT = board.FindFootprintByReference(des)
                            if fp:
                                fp.SetPosition(VECTOR2I(int(x),int(y)))
                                fp.SetOrientationDegrees(float(theta))
                                fp.SetDescription(name)

            except:
                raise Exception
                pass # no csv found

PullGroup().register()