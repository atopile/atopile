from atopile.model.model import Model
from atopile.data.toy_model import m as toy_model
from atopile.model.utils import EDGE_COLOR_DICT, VERTEX_COLOR_DICT, generate_uid_from_path

from atopile.visualiser.visualizer_model import UserInterface, UISchematic, UIModule, UIComponent, UISignal, UIPin, UIConnection, UIVertexEdgeGraph
import atopile.visualiser.utils as utils

import json as json
import yaml
import os


def generate_visualizer_window_config(user_interface: UserInterface):
    with open("src/visualiser_client/static/visualizer_config.json", "w") as f:
    # Write the dictionary to the file as a JSON object
        json.dump(user_interface.ui_settings, f)


def save_positions(return_data):
    
    #render_debug(toy_model, return_data)
    render_schematic(return_data)
    
    # export the return json dict for convenience
    with open("src/visualiser_client/static/return_data.json", "w") as f:
        json.dump(return_data, f)


def render_debug(model: Model, server_jointjs_return_data = None):
    # Instantiate a blank position config file
    graph_position_config = {}

    # We use the graph root uid to name the position file
    graph_root_uid = str(generate_uid_from_path(model.graph.vs[0]['path']))

    # Check if there is already a position config file
    if os.path.exists("src/visualiser_client/static/graph_position_config.yaml"):
        with open('src/visualiser_client/static/graph_position_config.yaml', 'r') as file:
            graph_position_config = yaml.safe_load(file)
            # Raise an error if the config file doesn't have the same uid
            if graph_position_config['graph_root_uid'] != graph_root_uid:
                raise ValueError('The position configuration does not match the current graph')
            
    # instantiate the graph
    ui_graph = UIVertexEdgeGraph()

    # Populate the graph with information coming from the model, the saved config and the server
    ui_graph.populate_graph(model, graph_position_config, server_jointjs_return_data)

    # Save the position config
    output_pos_config = {'graph_root_uid': graph_root_uid, "positions": ui_graph.export_positions()}
    with open("src/visualiser_client/static/graph_position_config.yaml", "w") as f:
        yaml.dump(output_pos_config, f, sort_keys=False)

    # Get the JointJS structure back from the graph
    v_e_list = ui_graph.to_jointjs()
    rendered_graph_json = {}
    rendered_graph_json['cells'] = v_e_list

    # Save the graph
    with open("src/visualiser_client/static/graph.json", "w") as f:
        json.dump(rendered_graph_json, f)

        
def render_schematic(server_jointjs_return_data = None):
    schematic = UISchematic()

    component1 = UIComponent(uid = 6)
    for i in range(6):
        pin = UIPin(number = i, uid = 10+i)
        component1.add_pin(pin)
    component1.update_position(utils.WindowPosition(150, 350))
    schematic.add_component(component1)

    component2 = UIComponent(uid = 4)
    for i in range(8):
        pin = UIPin(number = i, uid = 20+i)
        component2.add_pin(pin)
    component2.update_position(utils.WindowPosition(800, 600))
    schematic.add_component(component2)

    edge = UIConnection(source_comp=6,source_port=11,target_comp=4, target_port=21)
    schematic.add_connection(edge)

    module = UIModule(uid = 7)
    module.add_signal(UISignal(name='sig_1', uid = 44))
    module.add_signal(UISignal(name='sig_2', uid = 55))
    module.add_component(component1)
    module.add_component(component2)

    schematic.add_module(module)

    schematic.update_position(server_jointjs_return_data)

    # Save the graph
    rendered_graph_json = {}
    rendered_graph_json['cells'] = schematic.to_jointjs()
    with open("src/visualiser_client/static/graph.json", "w") as f:
        json.dump(rendered_graph_json, f)

if __name__ == "__main__":
    ui = UserInterface()
    generate_visualizer_window_config(ui)
    #render_debug(toy_model)
    render_schematic()