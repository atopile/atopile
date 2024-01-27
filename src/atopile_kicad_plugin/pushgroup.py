import csv
import os
from io import StringIO

from pcbnew import *

from atopile_kicad_plugin import log


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

class PullGroup(ActionPlugin):
    def defaults(self):
        self.name = "Push Group"
        self.category = "Push Group Layout Atopile"
        self.description = "Layout components on PCB in same spatial relationships as components on schematic"
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(os.path.dirname(__file__), 'upload.png') # Optional, defaults to ""

    def Run(self):
        board: BOARD = GetBoard()
        fn = board.GetFileName()
        prjpatha = fn.split('/')
        prjpath = '/'.join(prjpatha[:prjpatha.index('elec')])
        csv_file_path = '/'.join([prjpath,'build','default','group_map.csv'])
        heir = parse_hierarchy(csv_file_path)

        sel_gs = [g for g in board.Groups() if g.IsSelected()] #selected groups
        
        for sg in sel_gs:
            csv_table = StringIO()
            writer = csv.DictWriter(csv_table, fieldnames=['Name','x','y','theta'])
            writer.writeheader()

            g_name = sg.GetName()
            items = sg.GetItems()
            for item in items:
                if not 'Footprint' in item.GetFriendlyName(): continue
                item_ref = item.GetReference()
                x, y = item.GetPosition()
                theta = item.GetOrientationDegrees()
                writer.writerow(
                    {
                        "Name": heir[g_name].get(item_ref,''),
                        "x": x,
                        "y": y,
                        "theta": theta
                    }
                )
            with open('/'.join([prjpath,'.ato','modules',heir[g_name]['_package'],'elec','layout','layout.csv']), mode='w', newline='') as f:
                f.write(csv_table.getvalue())
        

        # for k in heir.keys():
        #     index = -1
        #     try:
        #         index = init_g_names.index(k)
        #         g = init_gs[index]
        #     except ValueError:
        #         index = -1
        #         g = PCB_GROUP(board)
        #         g.SetName(k)
        #         board.Add(g)
            
        #     # Populate group with footprints
        #     for comp in heir.get(k,{}):
        #         ref = comp.get('designator',None)
        #         if ref: 
        #             fp = board.FindFootprintByReference(ref)
        #             g.AddItem(fp)    

PullGroup().register()