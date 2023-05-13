from atopile.model.model import Model
from atopile.model.utils import generate_uid_from_path

from attrs import define, field

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

RECTANGLE_TYPES = {
    "component": {
        "strokeDasharray": None,
        "fill": "#FFFFFF"
    },
    "module": {
        "strokeDasharray": '4 2',
        "fill": 'transparent'
    },
}

@define
class WindowDimension:
    x_min: float
    x_max: float
    y_min: float
    y_max: float

@define
class WindowPosition:
    x: float = 0
    y: float = 0
# TODO: enfore usage in older parts of the code

@define
class ObjectDimension:
    width: float = 0
    height: float = 0


def map(value, input_min, input_max, output_min, output_max) -> float:
    return (value - input_min) * (output_max - output_min) / (input_max - input_min) + output_min

def window_coord_transform(coords: WindowPosition, source_dimension: WindowDimension, target_dimension: WindowDimension) -> WindowPosition:
    new_coords = WindowPosition()
    new_coords.x = map(coords.x, source_dimension.x_min, source_dimension.x_max, target_dimension.x_min, target_dimension.x_max)
    new_coords.y = map(coords.y, source_dimension.y_min, source_dimension.y_max, target_dimension.y_min, target_dimension.y_max)
    return new_coords

def get_coords_from_igraph(model: Model) -> dict:
    igraph_positions = {}
    graph_layout = model.graph.layout()

    igraph_min_x_dim = min(sublist[0] for sublist in graph_layout)
    igraph_max_x_dim = max(sublist[0] for sublist in graph_layout)
    igraph_min_y_dim = min(sublist[1] for sublist in graph_layout)
    igraph_max_y_dim = max(sublist[1] for sublist in graph_layout)

    igraph_dimension = WindowDimension(x_min = igraph_min_x_dim,
                                       x_max = igraph_max_x_dim,
                                       y_min = igraph_min_y_dim,
                                       y_max = igraph_max_y_dim)
    
    visualizer_dimension = WindowDimension(x_min = VISUALIZER_SETTINGS['margin_width'],
                                            x_max = VISUALIZER_SETTINGS['window_width'] - VISUALIZER_SETTINGS['margin_width'],
                                            y_min = VISUALIZER_SETTINGS['margin_height'],
                                            y_max = VISUALIZER_SETTINGS['window_height'] - VISUALIZER_SETTINGS['margin_height'])
    
    verticies = model.graph.vs
    for vertex in verticies:
        ig_vertex_pos = WindowPosition(x = graph_layout[vertex.index][0], y = graph_layout[vertex.index][1])
        vertex_pos = window_coord_transform(ig_vertex_pos, igraph_dimension, visualizer_dimension)
        vertex_uid = str(generate_uid_from_path(vertex['path']))
        igraph_positions[vertex_uid] = vertex_pos
    
    return igraph_positions

def generate_port_group(position: str) -> dict:
    return {
                "position": position,
                "label": {
                "position": {
                    "name": "outside",
                    "args": {
                    "offset": 10
                    }
                }
                },
                "attrs": {
                "portLabel": {
                    "fontFamily": "sans-serif",
                    "fontSize": 8
                },
                "portBody": {
                    "strokeWidth": 2,
                    "magnet": "active"
                }
                }
            }

def generate_rectangle_of_type(type: str, id: str, dimension: ObjectDimension, position: WindowPosition, z_layer: int = 0, port_groups: list = None, ports: list = None):
    return {
            "type": "standard.Rectangle",
            "position": {
                "x": position.x,
                "y": position.y
            },
            "size": {
                "width": dimension.width,
                "height": dimension.height
            },
            "angle": 0,
            "layer": "group1",
            "portMarkup": [
                {
                "tagName": "circle",
                "selector": "portBody",
                "attributes": {
                    "r": 3,
                    "fill": "#FFFFFF",
                    "stroke": "#333333"
                }
                }
            ],
            "portLabelMarkup": [
                {
                "tagName": "rect",
                "selector": "portLabelBackground"
                },
                {
                "tagName": "text",
                "selector": "portLabel",
                "attributes": {
                    "fill": "#333333"
                }
                }
            ],
            "ports": {
                "groups": port_groups,
                "items": ports
            },
            "id": id,
            "z": z_layer,
            "attrs": {
                "body": {
                "stroke": "#333333",
                "strokeDasharray": RECTANGLE_TYPES[type]["strokeDasharray"],
                "fill": RECTANGLE_TYPES[type]["fill"],
                "rx": 5,
                "ry": 5
                },
                "root": {
                "magnet": False
                }
            }
            }

def generate_vertex(uid: str, ref: str, color: str, position: WindowPosition) -> dict:
    return {
            "id": uid,
            "type": 'standard.Circle',
            "position": {
                "x": position.x,
                "y": position.y
            },
            "size": {
                "width": VISUALIZER_SETTINGS['vertex_size'],
                "height": VISUALIZER_SETTINGS['vertex_size']
            },
            "attrs": {
                "body": {
                "fill": color
                },
                "label": {
                    "text": ref,    
                    'font-family': VISUALIZER_SETTINGS['text']['font'],
                    'font-size': VISUALIZER_SETTINGS['text']['vertex_font_size']
                }
            }
        }

def generate_edge(source: str, target: str, type: str, color: str) -> dict:
    return {
            "type": "standard.Link",
            "source": {
                "id": source
            },
            "target": {
                "id": target
            },
            "labels": [{
                "attrs": {
                    'text': {
                        'text': type,
                        'font-family': VISUALIZER_SETTINGS['text']['font'],
                        'font-size': VISUALIZER_SETTINGS['text']['edge_font_size']

                    }}}],
            "attrs": {
                "line": {
                    "stroke": color,
                    'stroke-width': 2
                },
            }
        }

def generate_connection(source_comp: str, source_port: str, target_comp: str, target_port: str) -> dict:
    return {
            "type": "standard.Link",
            "source": {
                "port": source_port,
                "id": source_comp
            },
            "target": {
                "port": target_port,
                "id": target_comp
            },
            "z": -1,
            "labels": [{
                "attrs": {
                    'text': {
                        'text': None,
                        'font-family': VISUALIZER_SETTINGS['text']['font'],
                        'font-size': VISUALIZER_SETTINGS['text']['edge_font_size']

                    }}}],
            "router": {
                "name" : "orthogonal"
            },
            "attrs": {
                "line": {
                    "stroke": 'black',
                    'stroke-width': 2
                },
            }
        }

def get_extent_from_pos_and_dim(position: WindowPosition, dimension: ObjectDimension) -> WindowDimension:
    return WindowDimension(x_min = position.x, 
                            x_max = position.x + dimension.width, 
                            y_min = position.y, 
                            y_max = position.y + dimension.height)

