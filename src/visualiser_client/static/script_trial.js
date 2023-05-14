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

let generated_dict = {
    "name": "root",
    "type": "module",
    "uuid": "6dff5805-b5dd-4cb5-a091-2592ab75cb1c",
    "blocks": [
      {
        "name": "vdiv1",
        "type": "module",
        "uuid": "cc8fb500-8632-4912-9f87-7d9978e33a34",
        "blocks": [
          {
            "name": "R1",
            "type": "component",
            "uuid": "fe17f5d6-085b-4870-abe6-b8dab54df304",
            "blocks": [
              
            ],
            "ports": [
              {
                "name": "test",
                "uuid": "d84c783f-fa1c-42e4-b493-e3983c090046",
                "location": "top",
                "pins": [
                  {
                    "name": "p1",
                    "uuid": "024c699c-4daf-40d7-bd7a-84344ff77b4d",
                    "index": 0
                  }
                ]
              },
              {
                "name": "test2",
                "uuid": "d84c783f-fa1c-42e4-b493-e3983c090046",
                "location": "bottom",
                "pins": [
                  {
                    "name": "p2",
                    "uuid": "27136ec0-38ab-455a-854a-99108de0b3a3",
                    "index": 1
                  }
                ]
              }
            ],
            "links": [
              
            ]
          },
          {
            "name": "R2",
            "type": "component",
            "uuid": "3d67aaab-15ce-4ef5-b516-1d8e9df8b951",
            "blocks": [
              
            ],
            "ports": [
              {
                "name": "test",
                "uuid": "46f6824d-321a-4356-b324-c100fbd29300",
                "location": "top",
                "pins": [
                  {
                    "name": "p1",
                    "uuid": "898ff967-099a-4e86-b7fe-dfb6f91606ea",
                    "index": 0
                  }
                ]
              },
              {
                "name": "test2",
                "uuid": "46f6824d-321a-4356-b324-c100fbd29300",
                "location": "bottom",
                "pins": [
                  {
                    "name": "p2",
                    "uuid": "1afd78a9-aaa4-44aa-9f59-6903b835d4d9",
                    "index": 1
                  }
                ]
              }
            ],
            "links": [
              
            ]
          }
        ],
        "ports": [
          {
            "name": "test",
            "uuid": "a09e26c8-7408-4a5c-ae4c-be7a60cef65d",
            "location": "top",
            "pins": [
              {
                "name": "a",
                "uuid": "b4e2cf2a-5a9e-47f8-966c-b8e9c8483576",
                "index": 0
              }
            ]
          },
          {
            "name": "test2",
            "uuid": "1",
            "location": "left",
            "pins": [
              {
                "name": "center",
                "uuid": "05a26e8f-9c2d-4fee-a47f-6d05da5d9ef1",
                "index": 1
              }
            ]
          },
          {
            "name": "test3",
            "uuid": "2",
            "location": "bottom",
            "pins": [
              {
                "name": "b",
                "uuid": "114f8508-4c78-4ac8-8040-ee9e45c199e3",
                "index": 2
              }
            ]
          }
        ],
        "links": [
          {
            "name": "test",
            "uuid": "05b57934-029d-4eeb-af00-d067a36ce96e",
            "source": "024c699c-4daf-40d7-bd7a-84344ff77b4d",
            "target": "b4e2cf2a-5a9e-47f8-966c-b8e9c8483576"
          },
          {
            "name": "test",
            "uuid": "555c2026-69d5-401b-9eec-88e6a300356c",
            "source": "27136ec0-38ab-455a-854a-99108de0b3a3",
            "target": "05a26e8f-9c2d-4fee-a47f-6d05da5d9ef1"
          },
          {
            "name": "test",
            "uuid": "e3f0122b-232e-47e0-b237-f32bb451264e",
            "source": "898ff967-099a-4e86-b7fe-dfb6f91606ea",
            "target": "05a26e8f-9c2d-4fee-a47f-6d05da5d9ef1"
          },
          {
            "name": "test",
            "uuid": "e860c60b-d5ef-475d-bce9-8d1857705b54",
            "source": "1afd78a9-aaa4-44aa-9f59-6903b835d4d9",
            "target": "114f8508-4c78-4ac8-8040-ee9e45c199e3"
          }
        ]
      }
    ],
    "ports": [
      
    ],
    "links": [
      
    ]
  }

// Visual settings for the visualizer
let settings_dict = {
    "common": {
        "backgroundColor": 'rgba(224, 233, 227, 0.3)',
        "pinLabelFontSize": 12,
        "pinLabelPadding": 5,
        "parentPadding": 40
    },
    "component" : {
        "strokeWidth": 2,
        "fontSize": 10,
        "defaultWidth": 60,
        "defaultHeight": 80,
    },
    "block" : {
        "strokeWidth": 2,
        strokeDasharray: '4,4',
        "fontSize": 10
    },
    "link": {
        "strokeWidth": 1,
        "color": "blue"
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
        var padding = settings_dict['common']['parentPadding'];
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

// Class for a block
// For the moment, blocks and components are separate.
// We might want to combine them in the future.
class AtoBlock extends dia.Element {
    defaults() {
      return {
        ...super.defaults,
        type: "AtoBlock",
        size: { width: 10, height: 10 },
        collapsed: false,
        attrs: {
          body: {
            fill: "transparent",
            stroke: "#333",
            strokeWidth: settings_dict["block"]["strokeWidth"],
            strokeDasharray: settings_dict["block"]["strokeDasharray"],
            width: "calc(w)",
            height: "calc(h)"
          },
          label: {
            text: "Block",
            fill: "#333",
            fontSize: settings_dict["block"]["strokeWidth"],
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
    AtoBlock
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
                    name: "inside",
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
                        fontSize: settings_dict['common']['pinLabelFontSize'],
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
                'stroke': settings_dict['link']['color'],
                'stroke-width': settings_dict['link']['strokeWidth'],
                targetMarker: {'type': 'none'}
            },
            z: 0
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

function createBlock(title, uuid, ports_dict, x, y) {
    const block = new AtoBlock({
        id: uuid,
        attrs: {
            label: {
                text: title
            }
        }
    });

    addPortsAndPins(block, ports_dict);

    block.addTo(graph);
    block.position(x, y, { parentRelative: false });
    return block;
}

function addElementToElement(block_to_add, to_block) {
    to_block.embed(block_to_add);
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

    // If it is a block, create it
    else if (element['type'] == 'module') {
        let created_block = null
        console.log('made it')
        if (is_root == false) {
            created_block = createBlock(title = element['name'], uuid = element['uuid'], element['ports'], 100, 100);
        }
        if (parent) {
            addElementToElement(created_block, parent);
        }
        dict_of_elements[element['uuid']] = created_block;
        // Itterate over the included elements to create them
        for (let nested_element of element['blocks']) {
            let returned_dict = visulatizationFromDict(nested_element, is_root = false, created_block);
            console.log('returned dict keys ' + Object.keys(returned_dict) );//+ ' from ' + nested_element)
            //addElementsToElement(returned_dict, created_block);
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
        color: settings_dict["common"]["backgroundColor"]
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


let element_dict = visulatizationFromDict(generated_dict)



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



