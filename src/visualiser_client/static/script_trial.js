const { shapes, util, dia, anchors } = joint;

// Example input dict
let input_dict = {
    "name": "main",
    "type": "module",
    "uuid": 9,
    "ports": [],
    "modules": [
        {
        "name": "outer_comp_1",
        "uuid": 111,
        "type": "component",
        "ports": [
            {
                "name": "top",
                "uuid": 11,
                "location": "top",
                "pins": [
                    {
                        "name": "vcc",
                        "uuid": 1111,
                    }
                ]
            },
            {
                "name": "bottom",
                "uuid": 22,
                "location": "bottom",
                "pins": [
                    {
                        "name": "gnd",
                        "uuid": 2211,
                    }
                ]
            },
        ],
        "links": []
        },
        {
        "name": "main_module",
        "uuid": 3334,
        "type": "module",
        "modules": [
            {
                "name": "inner_comp_1",
                "uuid": 333,
                "type": "component",
                "ports": [
                    {
                        "name": "top",
                        "uuid": 33,
                        "location": "left",
                        "pins": [
                            {
                                "name": "vcc",
                                "uuid": 3311,
                            }
                        ]
                    },
                    {
                        "name": "bottom",
                        "uuid": 44,
                        "location": "right",
                        "pins": [
                            {
                                "name": "gnd",
                                "uuid": 4411,
                            }
                        ]
                    },
                ],
                "links": []
            },
            {
                "name": "inner_comp_2",
                "uuid": 555,
                "type": "component",
                "ports": [
                    {
                        "name": "top",
                        "uuid": 55,
                        "location": "left",
                        "pins": [
                            {
                                "name": "vcc",
                                "uuid": 5511,
                            }
                        ]
                    },
                    {
                        "name": "bottom",
                        "uuid": 66,
                        "location": "right",
                        "pins": [
                            {
                                "name": "gnd",
                                "uuid": 6611,
                            }
                        ]
                    },
                ],
                "links": []
            }
        ],
        "ports" : [
            {
                "name": "input",
                "uuid": 77,
                "location": "left",
                "pins": [
                    {
                        "name": "input",
                        "uuid": 7711,
                    }
                ]
            },
            {
                "name": "output",
                "uuid": 88,
                "location": "right",
                "pins": [
                    {
                        "name": "output",
                        "uuid": 8811,
                    }
                ]
            },
        ],
        "links": [
                {
                    "source": "7711",
                    "target": "6611"
                },
        ]
        }
    ],
    "links": [
        {
        "source": "1111",
        "target": "7711"
        }
    ]

}

// Visual settings for the visualizer
let settings_dict = {
    "paper": {
        "backgroundColor": 'rgba(224, 233, 227, 0.3)'
    },
    "component" : {
        "strokeWidth": 2,
        "fontSize": 10,
        "defaultWidth": 60,
        "defaultHeight": 60,
    },
    "module" : {
        "strokeWidth": 2,
        "fontSize": 10
    }
}

// Base class for the visual elements
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

// Class for a component
class AtoComponent extends AtoElement {
    defaults() {
        return {
            ...super.defaults(),
            type: "AtoComponent",
            size: { width: settings_dict["component"]["defaultWidth"], 
                    height: settings_dict["component"]["defaultHeight"] },
            attrs: {
                body: {
                    fill: "white",
                    z: 10,
                    stroke: "black",
                    strokeWidth: settings_dict["component"]["strokeWidth"],
                    width: "calc(w)",
                    height: "calc(h)",
                    rx: 5,
                    ry: 5
                },
                label: {
                    text: "Component",
                    fill: "black",
                    fontSize: settings_dict["component"]["fontSize"],
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
}

// Class for a module
// For the moment, modules and components are separate.
// We might want to combine them in the future.
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
            fontSize: settings_dict["module"]["strokeWidth"],
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


const cellNamespace = {
    ...shapes,
    AtoElement,
    AtoComponent,
    AtoModule
};

function addPortsAndPins(element, port_list) {
    // Dict of all the port for the element
    let port_groups = {};

    // Create the different ports
    for (let port of port_list) {
        port_groups[port['name']] = {
            position: {
                name: port['location'],
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
                    name: "outside",
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
        };

        // While we are creating the port, add the pins in the element
        for (let pin of port['pins']) {
            element.addPort({ 
                id: pin["uuid"],
                group: port['name'],
                attrs: { 
                    label: { 
                        text: pin['name'],
                        fontFamily: "sans-serif",
                    }
                }
            });
            pin_to_element_association[pin["uuid"]] = element["id"];
            //console.log('pin_uuid ' + pin["uuid"] + ' element ' + element["id"])
        }
    };

    // Add the ports list to the element
    element.prop({"ports": { "groups": port_groups}});
}

function addLinks(links) {
    for (let link of links) {
        var added_link = new shapes.standard.Link({
            source: {
                id: pin_to_element_association[link['source']],
                port: link['source']
            },
            target: {
                id: pin_to_element_association[link['target']],
                port: link['target']
            }
        });
        added_link.attr({
            line: {
                stroke: 'grey',
                'stroke-width': 3,
                targetMarker: {'type': 'none'}
            }
          });
        added_link.addTo(graph);
        //console.log('link added. src ' + link['source'] + ' parent ' + pin_to_element_association[link['source']] + ' tgt ' + link['target'])
    }
}

function createComponent(title, uuid, ports_dict, x, y) {
    const component = new AtoComponent({
        id: uuid,
        attrs: {
            label: {
                text: title
            }
        }
    });

    addPortsAndPins(component, ports_dict);

    component.addTo(graph);
    component.position(x, y, { parentRelative: true });
    return component;
}

function createModule(title, uuid, ports_dict, x, y) {
    const module = new AtoModule({
        id: uuid,
        attrs: {
            label: {
                text: title
            }
        }
    });

    addPortsAndPins(module, ports_dict);

    module.addTo(graph);
    module.position(x, y, { parentRelative: false });
    return module;
}

function addElementToElement(module_to_add, to_module) {
    to_module.embed(module_to_add);
}

function visulatizationFromDict(element, is_root = true, parent = null) {
    // Create the list of all the created elements
    let dict_of_elements = {};

    if (element['type'] == 'component') {
        let created_comp = createComponent(title = element['name'], uuid = element['uuid'], element['ports'], x = 100, y = 100);
        dict_of_elements[element['uuid']] = created_comp;
        if (parent) {
            addElementToElement(created_comp, parent);
        }
        //console.log('dict of element' + JSON.stringify(dict_of_elements[element['uuid']]));
    }

    // If it is a module, create it
    else if (element['type'] == 'module') {
        let created_module = null
        if (is_root == false) {
            created_module = createModule(title = element['name'], uuid = element['uuid'], element['ports'], 100, 100);
        }
        if (parent) {
            addElementToElement(created_module, parent);
        }
        dict_of_elements[element['uuid']] = created_module;
        // Itterate over the included elements to create them
        for (nested_element of element['modules']) {
            let returned_dict = visulatizationFromDict(nested_element, is_root = false, created_module);
            console.log('returned dict keys ' + Object.keys(returned_dict) );//+ ' from ' + nested_element)
            //addElementsToElement(returned_dict, created_module);
            // Add the returned list to the element list and add all sub-elements to it's parent
            dict_of_elements = { ...dict_of_elements, ...returned_dict };
        }

        addLinks(element['links']);
    }
    
    return dict_of_elements;
}

const graph = new dia.Graph({}, { cellNamespace });
const paper = new joint.dia.Paper({
    el: document.getElementById('atopilePaper'),
    model: graph,
    width: 1000,
    height: 600,
    gridSize: 10,
    drawGrid: true,
    background: {
        color: settings_dict["paper"]["backgroundColor"]
    },
    defaultRouter: { name: 'manhattan'},
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

let pin_to_element_association = {};


let element_dict = visulatizationFromDict(list = input_dict)




// var link = new shapes.standard.Link({
//     source: {
//         id: '111', //element_dict['111']['id'],
//         port: '1111'
//     },
//     target: {
//         id: '333',//element_dict['333']['id'],
//         port: '3311'
//     }
// });
// link.addTo(graph);

// let link2 = new shapes.standard.Link();
// link2.source('2211');
// link2.target('3311');
// link2.addTo(graph)


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



