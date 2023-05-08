from atopile.model.model2 import Model
from atopile.model.utils import EDGE_COLOR_DICT, VERTEX_COLOR_DICT, generate_uid_from_path

import atopile.visualiser.utils as utils

from attrs import define, field


@define
class Signal:
    name: str
    connect_to_pin: int = None

@define
class Pin:
    number: int

@define
class Component:
    id: str
    position: utils.WindowPosition = field(init=False)
    dimension: utils.ObjectDimension = field(init=False)
    extent: utils.WindowDimension  = field(init=False)
    pins: list = field(factory=list)
    signals: list = field(factory=list) # Might have to delete this

    def __attrs_post_init__(self):
        self.position = utils.WindowPosition(x = 10, y = 10)
        self.dimension = utils.ObjectDimension(width=40, height=10)
        self.extent = utils.get_extent_from_pos_and_dim(self.position, self.dimension)

    def add_pin(self) -> None:
        pin = Pin(number = len(self.pins))
        self.pins.append(pin)
        self.dimension.height = (len(self.pins) - len(self.pins)%2) * 20 if len(self.pins) > 1 else 20
        self.extent = utils.get_extent_from_pos_and_dim(self.position, self.dimension)
    
    def add_signal(self, signal: Signal) -> None: # Might have to delete this
        self.signals.append(signal)

    def update_position(self, position: utils.WindowPosition) -> None:
        self.position = position
        self.extent = utils.get_extent_from_pos_and_dim(self.position, self.dimension)

    def generate_jointjs_rep(self) -> dict:
        # Create the ports
        ports = []
        for pin in self.pins:

            group = 'right' if pin.number%2 else 'left'

            port = {
                "id": pin.number,
                "group": group,
                "attrs": {
                    "portLabel": {
                        "text": pin.number
                    }
                }
                }
            ports.append(port)

        port_groups = {}
        for side in ['left', 'right']:
            port_groups[side] = utils.generate_port_group(side)

        return utils.generate_rectangle_of_type('component', self.id, self.dimension, self.position, port_groups, ports)

@define
class Module:
    id: str
    position: utils.WindowPosition = field(init=False)
    dimension: utils.ObjectDimension = field(init=False)
    extent: utils.WindowDimension  = field(init=False)
    signals: list = field(factory=list)
    sub_components: list = field(factory=list)

    def __attrs_post_init__(self):
        self.position = utils.WindowPosition(x = 10, y = 10)
        self.dimension = utils.ObjectDimension(width=40, height=10)
        self.extent = utils.get_extent_from_pos_and_dim(self.position, self.dimension)

    def add_signal(self, signal: Signal) -> None:
        self.signals.append(signal)
    
    def add_component(self, sub_component: Component) -> None:
        self.sub_components.append(sub_component)

    def set_position(self, position: utils.WindowPosition) -> None:
        self.position = position
        self.extent = utils.get_extent_from_pos_and_dim(self.position, self.dimension)
    
    def update_bounding_box(self) -> None:
        # Calculate the position of the module
        self.extent.x_min = min(component.extent.x_min for component in self.sub_components) - 40
        self.extent.x_max = max(component.extent.x_max for component in self.sub_components) + 40
        self.extent.y_min = min(component.extent.y_min for component in self.sub_components) - 40
        self.extent.y_max = max(component.extent.y_max for component in self.sub_components) + 40

        self.dimension.width = self.extent.x_max - self.extent.x_min
        self.dimension.height = self.extent.y_max - self.extent.y_min
    
    def update_pos_dim_ext(self) -> None:
        self.update_bounding_box()
        self.position.x = self.extent.x_min
        self.position.y = self.extent.y_min
    
    def generate_jointjs_rep(self) -> dict:
        self.update_pos_dim_ext()
        # Create the ports
        ports = []
        for signal_nb, signal in enumerate(self.signals):

            group = 'right' if signal_nb%2 else 'left'

            port = {
                "id": signal.name,
                "group": group,
                "attrs": {
                    "portLabel": {
                        "text": signal.name
                    }
                }
                }
            ports.append(port)
        
        port_groups = {}
        for side in ['left', 'right']:
            port_groups[side] = utils.generate_port_group(side)


        return utils.generate_rectangle_of_type('module', self.id, self.dimension, self.position, port_groups, ports)


@define
class UIVertex:
    uid: str
    ref: str
    color: str
    position: utils.WindowPosition

    def to_jointjs(self) -> dict:
        return utils.generate_vertex(uid = self.uid,
                                     ref = self.ref,
                                     color = self.color,
                                     position = self.position)

@define
class UIEdge:
    source: int
    target: int
    type: str
    color: str

    def to_jointjs(self) -> dict:
        return utils.generate_edge(source = self.source,
                                     target = self.target,
                                     type = self.type,
                                     color = self.color)

class UIVertexEdgeGraph:
    def __init__(self) -> None:
        self.vertices = []
        self.edges = []

    def add_vertex(self, vertex: UIVertex) -> None:
        self.vertices.append(vertex)

    def add_edge(self, edge: UIEdge) -> None:
        self.edges.append(edge)

    def populate_graph(self, model: Model, graph_pos_config: dict = None, server_jointjs_return_data: dict = None) -> None:
        model_vertex_uid_list = []
        model_verticies = model.graph.vs
        for vertex in model_verticies:
            model_vertex_uid_list.append(str(generate_uid_from_path(vertex['path'])))
        
        vertex_positions = {}
        updated_vertex_pos_uid_list = []

        if server_jointjs_return_data is not None:
            for element in server_jointjs_return_data['cells']:
                if element['id'] in model_vertex_uid_list:
                    v_pos = utils.WindowPosition(x = element['position']['x'],
                                                y = element['position']['y'])
                    vertex_positions[element['id']] = v_pos
                    updated_vertex_pos_uid_list.append(element['id'])

        if graph_pos_config is not None:
            if len(graph_pos_config) != 0:
                for v_uid in graph_pos_config['positions']:
                    if v_uid not in updated_vertex_pos_uid_list:
                        v_pos = utils.WindowPosition(x = graph_pos_config['positions'][v_uid]['x'],
                                                    y = graph_pos_config['positions'][v_uid]['y'])
                        vertex_positions[v_uid] = v_pos
                        updated_vertex_pos_uid_list.append(v_uid)
        
        
        igraph_positions = utils.get_coords_from_igraph(model)
        for v_pos in igraph_positions:
            if v_pos not in updated_vertex_pos_uid_list:
                vertex_positions[v_pos] = igraph_positions[v_pos]
                updated_vertex_pos_uid_list.append(v_pos)
        

        for vertex in model_verticies:
            ui_vertex_uid = str(generate_uid_from_path(vertex['path']))
            ui_vertex_color = VERTEX_COLOR_DICT[vertex['type']]
            ui_vertex_position = vertex_positions[ui_vertex_uid]
            
            ui_vertex = UIVertex(uid = ui_vertex_uid, 
                                 ref = vertex['ref'],
                                 color = ui_vertex_color, 
                                 position = ui_vertex_position)
            
            self.add_vertex(ui_vertex)
        
        edges = model.graph.es

        for edge in edges:
            edge_source = str(generate_uid_from_path(model.graph.vs[edge.source]['path']))
            edge_target = str(generate_uid_from_path(model.graph.vs[edge.target]['path']))
            edge_type = edge['type']
            edge_color = EDGE_COLOR_DICT[edge_type]

            ui_edge = UIEdge(source = edge_source,
                             target = edge_target,
                             type = edge_type,
                             color = edge_color)
            
            self.add_edge(ui_edge)
    
    def export_positions(self) -> dict:
        pos_dict = {}
        for vertex in self.vertices:
            pos_dict[vertex.uid] = {'x': vertex.position.x, 'y': vertex.position.y}

        return pos_dict
    
    def to_jointjs(self) -> list:
        jointjs_vertex_edge_list = []
        
        for vertex in self.vertices:
            jointjs_vertex_edge_list.append(vertex.to_jointjs())
        
        for edge in self.edges:
            jointjs_vertex_edge_list.append(edge.to_jointjs())

        return jointjs_vertex_edge_list


@define
class UserInterface:
    ui_settings: dict = utils.VISUALIZER_SETTINGS