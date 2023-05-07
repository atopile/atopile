from attrs import define, field, Factory
import attr

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
    x: float
    y: float
# TODO: enfore usage in older parts of the code

@define
class ObjectDimension:
    width: float
    height: float

@define
class Signal:
    name: str
    connect_to_pin: int = None

@define
class Pin:
    number: int

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

def generate_rectangle_of_type(type: str, id: str, dimension: ObjectDimension, position: WindowPosition, port_groups: list = None, ports: list = None):
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
            "z": 1,
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

def get_extent_from_pos_and_dim(position: WindowPosition, dimension: ObjectDimension) -> WindowDimension:
    return WindowDimension(x_min = position.x, 
                            x_max = position.x + dimension.width, 
                            y_min = position.y, 
                            y_max = position.y + dimension.height)

@define
class Component:
    id: str
    position: WindowPosition = field(init=False)
    dimension: ObjectDimension = field(init=False)
    extent: WindowDimension  = field(init=False)
    pins: list = field(factory=list)
    signals: list = field(factory=list) # Might have to delete this

    def __attrs_post_init__(self):
        self.position = WindowPosition(x = 10, y = 10)
        self.dimension = ObjectDimension(width=40, height=10)
        self.extent = get_extent_from_pos_and_dim(self.position, self.dimension)

    def add_pin(self) -> None:
        pin = Pin(number = len(self.pins))
        self.pins.append(pin)
        self.dimension.height = (len(self.pins) - len(self.pins)%2) * 20 if len(self.pins) > 1 else 20
        self.extent = get_extent_from_pos_and_dim(self.position, self.dimension)
    
    def add_signal(self, signal: Signal) -> None: # Might have to delete this
        self.signals.append(signal)

    def update_position(self, position: WindowPosition) -> None:
        self.position = position
        self.extent = get_extent_from_pos_and_dim(self.position, self.dimension)

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
            port_groups[side] = generate_port_group(side)

        return generate_rectangle_of_type('component', self.id, self.dimension, self.position, port_groups, ports)

@define
class Module:
    id: str
    position: WindowPosition = field(init=False)
    dimension: ObjectDimension = field(init=False)
    extent: WindowDimension  = field(init=False)
    signals: list = field(factory=list)
    sub_components: list = field(factory=list)

    def __attrs_post_init__(self):
        self.position = WindowPosition(x = 10, y = 10)
        self.dimension = ObjectDimension(width=40, height=10)
        self.extent = get_extent_from_pos_and_dim(self.position, self.dimension)

    def add_signal(self, signal: Signal) -> None:
        self.signals.append(signal)
    
    def add_component(self, sub_component: Component) -> None:
        self.sub_components.append(sub_component)

    def set_position(self, position: WindowPosition) -> None:
        self.position = position
        self.extent = get_extent_from_pos_and_dim(self.position, self.dimension)
    
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
            port_groups[side] = generate_port_group(side)


        return generate_rectangle_of_type('module', self.id, self.dimension, self.position, port_groups, ports)
    
