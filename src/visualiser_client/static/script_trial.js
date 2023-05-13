const { shapes, util, dia, anchors } = joint;

let input_dict = {
    "name": "main_module",
    "type": "module",
    "modules": [
        {
            "name": "inner_comp_1",
            "type": "component",
            "ports": [
                {
                    "name": "top",
                    "pins": [
                        {
                            "name": "vcc",
                        }
                    ]
                },
                {
                    "name": "bottoms",
                    "pins": [
                        {
                            "name": "vcc",
                        }
                    ]
                },
            ],
            "links": []
        },
        {
            "name": "inner_comp_2",
            "type": "component",
            "ports": [
                {
                    "name": "top",
                    "pins": [
                        {
                            "name": "vcc",
                        }
                    ]
                },
                {
                    "name": "bottoms",
                    "pins": [
                        {
                            "name": "vcc",
                        }
                    ]
                },
            ],
            "links": []
        }
    ],
    "links": [
        {
            "source": "inner_comp_1.vcc",
            "target": "inner_comp_2.gnd"
        }
    ]
}

let settings_dict = {
    "default": {
        "strokeWidth": 2
    },
    "component" : {
        "strokeWidth": 6
    },
    "module" : {
        "strokeWidth": 4
    }
}

console.log(settings_dict["module"]["strokeWidth"]);

class AtoElement extends dia.Element {
    defaults() {
        return {
            ...super.defaults,
            hidden: false
        };
    }

    isHidden() {
        return Boolean(this.get("hidden"));
    }

    static isAtoElement(shape) {
        return shape instanceof AtoElement;
    }
}

class AtoComponent extends AtoElement {
    defaults() {
        return {
            ...super.defaults(),
            type: "AtoComponent",
            size: { width: 200, height: 50 },
            attrs: {
                body: {
                    fill: "white",
                    z: 10,
                    stroke: "black",
                    strokeWidth: settings_dict["default"]["strokeWidth"],
                    width: "calc(w)",
                    height: "calc(h)",
                    rx: 5,
                    ry: 5
                },
                label: {
                    text: "Component",
                    fill: "black",
                    fontSize: 12,
                    fontWeight: "bold",
                    textVerticalAnchor: "middle",
                    textAnchor: "middle",
                    fontFamily: "sans-serif",
                    x: "calc(w/2)",
                    y: "calc(h/2)"
                }
            }
        };
    }

    preinitialize() {
        this.markup = util.svg`
            <rect @selector="body" />
            <text @selector="label" />
        `;
    }

    addConnection(name, port) {
        this.addPort({ 
            group: port,
            attrs: { 
                label: { 
                    text: name,
                    fontFamily: "sans-serif",
                }
            }
        });
    }

    fitAncestorElements() {
        var padding = 40;
        this.fitParent({
            deep: true,
            padding: {
                top: padding,
                left: padding,
                right: padding,
                bottom: padding
            }
        });
    }

    addNewPort(groupName, side) {
        this.prop({ports: { // This section describes what a port looks like
                    groups: {
                        [groupName]: {
                        position: {
                            name: side
                        },
                        attrs: {
                            portBody: {
                                magnet: true,
                                r: 5,
                                fill: '#FFFFFF',
                                stroke:'#023047'
                            }
                        },
                        label: {
                            position: {
                                name: side,
                                args: { y: 0 }
                            },
                            markup: [{
                                tagName: 'text',
                                selector: 'label',
                                className: 'label-text'
                            }]
                        },
                        markup: [{
                            tagName: 'circle',
                            selector: 'portBody'
                        }]
                    }
                    }
                }
            });
    }
}


class AtoModule extends dia.Element {
    defaults() {
      return {
        ...super.defaults,
        type: "AtoModule",
        size: { width: 200, height: 200 },
        collapsed: false,
        attrs: {
          body: {
            fill: "transparent",
            stroke: "#333",
            strokeWidth: settings_dict["module"]["strokeWidth"],
            width: "calc(w)",
            height: "calc(h)"
          },
          label: {
            text: "Module",
            fill: "#333",
            fontSize: 12,
            fontWeight: "bold",
            textVerticalAnchor: "middle",
            textAnchor: "middle",
            fontFamily: "sans-serif",
            x: "calc(w / 2)"
          }
        }
      };
    }
  
    preinitialize(...args) {
      this.markup = util.svg`
              <rect @selector="body" />
              <text @selector="label" />
          `;
    }
  
    updateChildrenVisibility() {
      const collapsed = this.isCollapsed();
      this.getEmbeddedCells().forEach((child) => child.set("hidden", collapsed));
    }

    fitAncestorElements() {
        var padding = 10;
        this.fitParent({
            deep: true,
            padding: {
                top:  padding,
                left: padding,
                right: padding,
                bottom: padding
            }
        });
    }
  }




function buildClassesFromDict(dict) {
    let module = new Module(dict.info);
    for (let subModule of dict.modules) {
        module.addModule(buildClassesFromDict(subModule));
    }
    for (let component of dict.components) {
        module.addComponent(buildClassesFromDict(component, true));
    }
    return module;
    
}

const cellNamespace = {
    ...shapes,
    AtoElement,
    AtoComponent,
    AtoModule
};

function createComponent(title, x, y) {
    const component = new AtoComponent({
        attrs: {
            label: {
                text: title
            }
        }
    });
    component.addTo(graph);
    component.position(x, y, { parentRelative: true });
    return component;
}

function createModule(title, x, y) {
    const module = new AtoModule({
        attrs: {
            label: {
                text: title
            }
        }
    });
    module.addTo(graph);
    module.position(x, y, { parentRelative: false });
    return module;
}

function addModuleToModule(module_to_add, to_module) {
    to_module.embed(module_to_add);
}

const graph = new dia.Graph({}, { cellNamespace });
const paper = new joint.dia.Paper({
    el: document.getElementById('myholder'),
    model: graph,
    width: 600,
    height: 600,
    gridSize: 10,
    drawGrid: true,
    background: {
        color: 'rgba(0, 255, 0, 0.3)'
    },
    cellViewNamespace: cellNamespace,
    // restrictTranslate: (elementView) => {
    //     const parent = elementView.model.getParentCell();
    //     if (!parent) return null; // No restriction
    //     // Activity movement is constrained by the parent area
    //     const { x, y, width, height } = parent.getBBox();
    //     return new g.Rect(
    //       x,
    //       y,
    //       width,
    //       height
    //     ).inflate(10);
    //   },
});
module2 = createModule("module2", 100, 100)
module1 = createModule('this is a module', 10, 10)
test = createComponent('allo', 10, 10);
test.addNewPort('port 1', 'right');
test.addConnection('pin 1', 'port 1');
test.addConnection('pin 3', 'port 1');
test.addNewPort('port 2', 'left');
test.addConnection('pin 2', 'port 2');
test.addConnection('pin 4', 'port 2');

comp2 = createComponent('comp2', 10, 10);



addModuleToModule(module1, module2)


addModuleToModule(test, module1);
addModuleToModule(comp2, module1);

var ports = test.getPorts();
console.log(ports);
console.log(typeof ports);
ports.forEach(element => {
    console.log(element);
});

console.log(test.getGroupPorts('port 1'));
console.log('new stuff');

let result = test.prop('ports/groups');
console.log(result);
console.log(typeof result);






test.resize(100, 100);

paper.on('cell:pointerup', function(evt, x, y) {
    const requestOptions = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(graph.toJSON()) // << data going the other way
    };
    fetch('/api/graph', requestOptions);
});

paper.on('element:pointermove', function(elementView) {
    var element = elementView.model;
    // `fitAncestorElements()` method is defined at `joint.shapes.container.Base` in `./joint.shapes.container.js`
    element.fitAncestorElements();
});



