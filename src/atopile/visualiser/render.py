# for now, statically import the "toy_model" or something you want to use as a demo
from atopile.data.toy_model import m as toy_model
from atopile.model.utils import EDGE_COLOR_DICT, VERTEX_COLOR_DICT

import json as json
from attrs import define

VISUALIZER_SETTINGS = {
    'background_color': 'rgba(140, 146, 172, 0.3)',
    'grid_size': 15,
    'draw_grid': True,
    'window_width': 1400,
    'window_height': 900,
    'margin_width': 100,
    'margin_height': 100,
}

@define
class WindowDimension:
    x_max: float
    x_min: float
    y_max: float
    y_min: float

def generate_visualizer_window_config():
    visualizer_config = VISUALIZER_SETTINGS

    with open("src/visualiser_client/static/visualizer_config.json", "w") as f:
    # Write the dictionary to the file as a JSON object
        json.dump(visualizer_config, f)

def window_coord_transform(coords: list, source_dimension: WindowDimension, target_dimension: WindowDimension):
    new_coords = []
    new_coords.append((coords[0] - source_dimension.x_min) * (target_dimension.x_max - target_dimension.x_min) / (source_dimension.x_max - source_dimension.x_min) + target_dimension.x_min)
    new_coords.append((coords[1] - source_dimension.y_min) * (target_dimension.y_max - target_dimension.y_min) / (source_dimension.y_max - source_dimension.y_min) + target_dimension.y_min)
    return new_coords

## in this file we should make a jointjs dict
def render():
    graph_layout = toy_model.graph.layout()

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


    verticies = toy_model.graph.vs

    rendered_graph_json = {}
    rendered_graph_json['cells'] = []

    for vertex in verticies:
        vertex_position = window_coord_transform(graph_layout[vertex.index], igraph_dimension, visualizer_dimension)
        vertex_color = VERTEX_COLOR_DICT[vertex['type']]
        vertex_json_dict = {
            "id": vertex.index+1,
            "type": 'standard.Circle',
            "position": {
                "x": vertex_position[0],
                "y": vertex_position[1]
            },
            "size": {
                "width": 50,
                "height": 50
            },
            "attrs": {
                "body": {
                "fill": vertex_color
                },
                "label": {
                    "text": vertex['ref'],    
                    'font-family': 'Helvetica',
                    'font-size': 10
                }
            }
        }
        
        rendered_graph_json['cells'].append(vertex_json_dict)

        #print(rendered_graph_json['cells'])
    
    edges = toy_model.graph.es

    for edge in edges:
        edge_source = edge.source+1
        edge_target = edge.target+1
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
                        'font-family': 'Helvetica',
                        'font-size': 10

                    }}}],
            "attrs": {
                "line": {
                    "stroke": edge_color,
                    'stroke-width': 2
                },
            }
        }
        
        rendered_graph_json['cells'].append(edge_json_dict)


    # Open a file for writing
    with open("src/visualiser_client/static/graph.json", "w") as f:
    # Write the dictionary to the file as a JSON object
        json.dump(rendered_graph_json, f)
        


# In here, we get the graph, for each vertex in the graph, we generate
# an onject in the JSON. We then connect the edges together 

if __name__ == "__main__":
    generate_visualizer_window_config()
    render()