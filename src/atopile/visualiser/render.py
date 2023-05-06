# for now, statically import the "toy_model" or something you want to use as a demo
from atopile.data.toy_model import m as toy_model
from atopile.model.utils import EDGE_COLOR_DICT, VERTEX_COLOR_DICT

import json as json

def igraph_to_render_coord_transform(coords):
    new_coords = []
    for coord in coords:
        new_coords.append(70 * (coord + 7))

    return new_coords

## in this file we should make a jointjs dict
def render():
    layout = toy_model.graph.layout()

    # Get the position of vertex 0
    pos = layout[0]

    print(pos)
    print('this is a test')

    verticies = toy_model.graph.vs
    print(type(verticies))

    rendered_graph_json = {}
    rendered_graph_json['cells'] = []

    for vertex in verticies:
        vertex_position = igraph_to_render_coord_transform(layout[vertex.index])
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
    render()