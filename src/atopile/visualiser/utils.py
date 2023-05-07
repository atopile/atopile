from attrs import define

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

class Component:
    def __init__(self, pin_number: int, comp_id: str, position: WindowPosition, pin_names: list = None) -> None:
        comp_width = 60
        comp_height = pin_number / 2 * 40

        # Create the ports
        self.ports = []
        for pin in range(pin_number):

            pin_name = pin_names[pin] if pin_names else pin
            group = 'right' if pin%2 else 'left'

            port = {
                "id": pin,
                "group": group,
                "attrs": {
                    "portLabel": {
                        "text": pin_name
                    }
                }
                }
            self.ports.append(port)
        
        self.port_groups = {}
        for side in ['left', 'right']:
            port_group = {
                "position": side,
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
            self.port_groups[side] = port_group
        
        self.comp_struct = {
            "type": "standard.Rectangle",
            "position": {
                "x": position.x,
                "y": position.y
            },
            "size": {
                "width": comp_width,
                "height": comp_height
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
                "groups": self.port_groups,
                "items": self.ports
            },
            "id": comp_id,
            "z": 1,
            "attrs": {
                "body": {
                "stroke": "#333333",
                "fill": "#fff",
                "rx": 5,
                "ry": 5
                },
                "root": {
                "magnet": False
                }
            }
            }

        