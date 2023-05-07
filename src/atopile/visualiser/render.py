# for now, statically import the "toy_model" or something you want to use as a demo
from atopile.model.model2 import Model
from atopile.data.toy_model import m as toy_model
from atopile.model.utils import EDGE_COLOR_DICT, VERTEX_COLOR_DICT, generate_uid_from_path

from atopile.visualiser.utils import WindowDimension, WindowPosition, Component

import json as json
import yaml
import os

VISUALIZER_SETTINGS = {
    'background_color': 'rgba(140, 146, 172, 0.3)',
    'grid_size': 15,
    'draw_grid': True,
    'window_width': 1400,
    'window_height': 900,
    'margin_width': 100,
    'margin_height': 100,
    'vertex_size': 40,
    'text': {
        'font': 'Helvetica',
        'vertex_font_size': 10,
        'edge_font_size': 7
    }
}


def generate_visualizer_window_config():
    visualizer_config = VISUALIZER_SETTINGS

    with open("src/visualiser_client/static/visualizer_config.json", "w") as f:
    # Write the dictionary to the file as a JSON object
        json.dump(visualizer_config, f)

def map(value, input_min, input_max, output_min, output_max) -> float:
    return (value - input_min) * (output_max - output_min) / (input_max - input_min) + output_min

def window_coord_transform(coords: list, source_dimension: WindowDimension, target_dimension: WindowDimension):
    new_coords = {}
    new_coords['x'] = map(coords[0], source_dimension.x_min, source_dimension.x_max, target_dimension.x_min, target_dimension.x_max)
    new_coords['y'] = map(coords[1], source_dimension.y_min, source_dimension.y_max, target_dimension.y_min, target_dimension.y_max)
    return new_coords

def get_coords_from_igraph(model: Model):
    igraph_positions = {}
    graph_layout = model.graph.layout()

    igraph_max_x_dim = max(sublist[0] for sublist in graph_layout)
    igraph_min_x_dim = min(sublist[0] for sublist in graph_layout)
    igraph_max_y_dim = max(sublist[1] for sublist in graph_layout)
    igraph_min_y_dim = min(sublist[1] for sublist in graph_layout)

    igraph_dimension = WindowDimension(x_max = igraph_max_x_dim,
                                       x_min = igraph_min_x_dim,
                                       y_max = igraph_max_y_dim,
                                       y_min = igraph_min_y_dim)
    
    visualizer_dimension = WindowDimension(x_max = VISUALIZER_SETTINGS['window_width'] - VISUALIZER_SETTINGS['margin_width'],
                                            x_min = VISUALIZER_SETTINGS['margin_width'],
                                            y_max = VISUALIZER_SETTINGS['window_height'] - VISUALIZER_SETTINGS['margin_height'],
                                            y_min = VISUALIZER_SETTINGS['margin_height'])
    
    verticies = model.graph.vs
    for vertex in verticies:
        vertex_position = window_coord_transform(graph_layout[vertex.index], igraph_dimension, visualizer_dimension)
        vertex_uid = str(generate_uid_from_path(vertex['path']))
        igraph_positions[vertex_uid] = vertex_position
    
    return igraph_positions


def save_positions(return_data):
    position_config = {}
    # Load the previous config
    with open('src/visualiser_client/static/position_config.yaml', 'r') as file:
        position_config = yaml.safe_load(file)
    
    uid_list = position_config['positions'].keys()

    new_positions = {}
    for element in return_data['cells']:
        if element['id'] in uid_list:
            new_positions[element['id']] = element['position']
    
    position_config['positions'] = new_positions
    print(position_config)
    with open("src/visualiser_client/static/position_config.yaml", "w") as f:
        yaml.dump(position_config, f, sort_keys=False, default_flow_style=False)
    
    render_debug(toy_model)
    
    # export the return json dict for convenience
    with open("src/visualiser_client/static/return_data.json", "w") as f:
        json.dump(return_data, f)


def render_debug(model: Model):
    
    position_config = {}
    config_uid_list = []
    graph_root_uid = str(generate_uid_from_path(model.graph.vs[0]['path']))
    if os.path.exists("src/visualiser_client/static/position_config.yaml"):
        with open('src/visualiser_client/static/position_config.yaml', 'r') as file:
            # Load the contents of the YAML file as a Python object
            position_config = yaml.safe_load(file)
            if position_config['graph_root_uid'] != graph_root_uid:
                raise ValueError('The position configuration does not match the current graph')
            config_uid_list = position_config['positions'].keys()
    else:
        position_config = {'graph_root_uid': graph_root_uid}
    
    igraph_positions = get_coords_from_igraph(model)

    vertex_positions = {}

    rendered_graph_json = {'cells': []}

    verticies = model.graph.vs
    for vertex in verticies:
        vertex_uid = str(generate_uid_from_path(vertex['path']))
        if vertex_uid in config_uid_list:
            vertex_positions[vertex_uid] = position_config['positions'][vertex_uid]
        else:
            vertex_positions[vertex_uid] = igraph_positions[vertex_uid]
        vertex_color = VERTEX_COLOR_DICT[vertex['type']]
        vertex_json_dict = {
            "id": vertex_uid,
            "type": 'standard.Circle',
            "position": {
                "x": vertex_positions[vertex_uid]['x'],
                "y": vertex_positions[vertex_uid]['y']
            },
            "size": {
                "width": VISUALIZER_SETTINGS['vertex_size'],
                "height": VISUALIZER_SETTINGS['vertex_size']
            },
            "attrs": {
                "body": {
                "fill": vertex_color
                },
                "label": {
                    "text": vertex['ref'],    
                    'font-family': VISUALIZER_SETTINGS['text']['font'],
                    'font-size': VISUALIZER_SETTINGS['text']['vertex_font_size']
                }
            }
        }
        
        rendered_graph_json['cells'].append(vertex_json_dict)

    # Update the config based on the new added vertices
    position_config['positions'] = vertex_positions
    
    # Save the config
    with open("src/visualiser_client/static/position_config.yaml", "w") as f:
        yaml.dump(position_config, f, sort_keys=False)

    edges = model.graph.es

    for edge in edges:
        edge_source = str(generate_uid_from_path(model.graph.vs[edge.source]['path']))
        edge_target = str(generate_uid_from_path(model.graph.vs[edge.target]['path']))
        edge_color = EDGE_COLOR_DICT[edge['type']]
        edge_json_dict = {
            "type": "standard.Link",
            "source": {
                "id": edge_source
            },
            "target": {
                "id": edge_target
            },
            "labels": [{
                "attrs": {
                    'text': {
                        'text': edge['type'],
                        'font-family': VISUALIZER_SETTINGS['text']['font'],
                        'font-size': VISUALIZER_SETTINGS['text']['edge_font_size']

                    }}}],
            "attrs": {
                "line": {
                    "stroke": edge_color,
                    'stroke-width': 2
                },
            }
        }
        
        rendered_graph_json['cells'].append(edge_json_dict)

    # Save the graph
    with open("src/visualiser_client/static/graph.json", "w") as f:
        json.dump(rendered_graph_json, f)
        
def render_schematic():

    rendered_graph_json = {'cells': []}

    vertex_json_dict = {
        "id": 1,
        "type": 'standard.Circle',
        "position": {
            "x": 100,
            "y": 100
        },
        "size": {
            "width": VISUALIZER_SETTINGS['vertex_size'],
            "height": VISUALIZER_SETTINGS['vertex_size']
        },
        "attrs": {
            "body": {
            "fill": 'blue'
            },
            "label": {
                "text": 'test',    
                'font-family': VISUALIZER_SETTINGS['text']['font'],
                'font-size': VISUALIZER_SETTINGS['text']['vertex_font_size']
            }
        }
    }
    rendered_graph_json['cells'].append(vertex_json_dict)
    vertex_json_dict = {
        "id": 2,
        "type": 'standard.Rectangle',
        "position": {
            "x": 100,
            "y": 100
        },
        "size": {
            "width": VISUALIZER_SETTINGS['vertex_size'],
            "height": VISUALIZER_SETTINGS['vertex_size']
        },
        "attrs": {
            "body": {
            "fill": 'blue'
            },
            "label": {
                "text": 'test',    
                'font-family': VISUALIZER_SETTINGS['text']['font'],
                'font-size': VISUALIZER_SETTINGS['text']['vertex_font_size']
            }
        }
    }
    rendered_graph_json['cells'].append(vertex_json_dict)

    edge_json_dict = {
        "type": "standard.Link",
        "source": {
            "id": 1
        },
        "target": {
            "id": 2
        },
        "labels": [{
            "attrs": {
                'text': {
                    'text': 'test',
                    'font-family': VISUALIZER_SETTINGS['text']['font'],
                    'font-size': VISUALIZER_SETTINGS['text']['edge_font_size']

                }}}],
        "router": {
                "name" : "orthogonal",
        },
        "attrs": {
            "line": {
                "stroke": 'black',
                'stroke-width': 2
            },
        }
    }

    #rendered_graph_json['cells'].append(vertex_json_dict)
    #rendered_graph_json['cells'].append(edge_json_dict)

    component = Component(pin_number = 4, comp_id = 6, position = WindowPosition(10,10))
    rendered_graph_json['cells'].append(component.comp_struct)

    # Save the graph
    with open("src/visualiser_client/static/graph.json", "w") as f:
        json.dump(rendered_graph_json, f)

if __name__ == "__main__":
    generate_visualizer_window_config()
    #render_debug(toy_model)
    render_schematic()