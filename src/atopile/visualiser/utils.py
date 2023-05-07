from attrs import define, field

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
    x_max: float
    x_min: float
    y_max: float
    y_min: float

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
    connect_to_pin: int

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

@define
class Module:
    id: str
    position: WindowPosition = WindowPosition(x = 0, y = 0)
    dimension: ObjectDimension = ObjectDimension(width=60, height=60)
    signals: list = field(factory=list)

    def add_signal(self, signal: Signal) -> None:
        self.signals.append(signal)
    
    def generate_jointjs_rep(self) -> dict:
        return generate_rectangle_of_type('module', self.id, self.dimension, self.position)
    

@define
class Component:
    id: str
    position: WindowPosition = WindowPosition(x = 0, y = 0)
    dimension: ObjectDimension = ObjectDimension(width=40, height=10)
    pins: list = field(factory=list)
    signals: list = field(factory=list)

    def add_pin(self) -> None:
        pin = Pin(number = len(self.pins))
        self.pins.append(pin)
    
    def add_signal(self, signal: Signal) -> None:
        self.signals.append(signal)

    def generate_jointjs_rep(self) -> dict:
        self.dimension.height = len(self.pins) / 2 * 40

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
