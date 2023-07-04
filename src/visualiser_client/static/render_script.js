const { shapes, util, dia, anchors } = joint;

// Visual settings for the visualizer
let settings_dict = {
    common: {
        backgroundColor: 'rgba(224, 233, 227, 0.3)',
        gridSize: 5,
        parentPadding: 50,
        fontFamily: "monospace",
        fontHeightToPxRatio: 1.6,
        fontLengthToPxRatio: 0.7,
    },
    component : {
        strokeWidth: 2,
        fontSize: 8,
        fontWeight: "bold",
        defaultWidth: 60,
        portPitch: 20,
        defaultHeight: 50,
        labelHorizontalMargin: 40,
        labelVerticalMargin: 10,
        titleMargin: 10,
        pin: {
            fontSize: 8,
            fontWeight: "normal",
        },
    },
    block : {
        strokeWidth: 2,
        boxRadius: 5,
        strokeDasharray: '4,4',
        label: {
            fontSize: 10,
            fontWeight: "bold",
        }
    },
    link: {
        strokeWidth: 1,
        color: "blue"
    },
    stubs: {
        fontSize: 10,
    }
}

let opposite_direction = {
    "top": "bottom",
    "bottom": "top",
    "left": "right",
    "right": "left"
}

// Base class for the visual elements
class AtoElement extends dia.Element {
    defaults() {
        return {
            ...super.defaults,
            hidden: false,
        };
    }

    isHidden() {
        return Boolean(this.get("hidden"));
    }

    static isAtoElement(shape) {
        return shape instanceof AtoElement;
    }

    addPortWithPins(port_name, port_location, pin_list) {
        let port_label_position = getPortLabelPosition(port_location);
        let port_anchor = getPortLabelAnchor(port_location);
        let port_angle = getPortLabelAngle(port_location);
        let port_position = getPortPosition(port_location);

        let port_group = {};

        port_group[port_name] = {
            position: port_position,
            attrs: {
                portBody: {
                    magnet: true,
                    r: 2,
                    fill: '#FFFFFF',
                    stroke:'#023047',
                },
            },
            label: {
                position: {
                    args: {
                        x: port_label_position[0],
                        y: port_label_position[1],
                        angle: port_angle,
                    }, // Can't use inside/outside in combination
                    //name: 'inside'
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
        for (let pin of pin_list) {
            this.addPort({
                id: pin["uuid"],
                group: port_name,
                attrs: {
                    label: {
                        text: pin['name'],
                        fontFamily: settings_dict['common']['fontFamily'],
                        fontSize: settings_dict['component']['pin']['fontSize'],
                        fontWeight: settings_dict["component"]['pin']["fontWeight"],
                        textAnchor: port_anchor,
                    },
                },
            });
        }

        // Add the ports list to the element
        this.prop({"ports": { "groups": port_group}});
    }
}

// Class for a component
class AtoComponent extends AtoElement {
    defaults() {
        return {
            ...super.defaults(),
            type: "AtoComponent",
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
                    fontWeight: settings_dict["component"]["fontWeight"],
                    textVerticalAnchor: "middle",
                    textAnchor: "middle",
                    fontFamily: settings_dict["common"]["fontFamily"],
                    textWrap: {
                        width: 100,
                    },
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
                height: "calc(h)",
                rx: settings_dict["block"]["boxRadius"],
                ry: settings_dict["block"]["boxRadius"],
            },
            label: {
                text: "Block",
                fill: "#333",
                textVerticalAnchor: "top",
                fontFamily: settings_dict['common']['fontFamily'],
                fontSize: settings_dict['block']['label']['fontSize'],
                fontWeight: settings_dict["block"]['label']["fontWeight"],
                textAnchor: 'start',
                x: 8,
                y: 8
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

function getPortLabelPosition(location) {
    switch (location) {
        case "top":
            return [0, 8];
        case "bottom":
            return [0, -8];
        case "left":
            return [5, 0];
        case "right":
            return [-5, 0];
        default:
            return [0, 0];
    };
};

function getPortLabelAnchor(location) {
    switch (location) {
        case "top":
            return 'end';
        case "bottom":
            return 'start';
        case "left":
            return 'start';
        case "right":
            return 'end';
        default:
            return 'middle';
    }
};

function getPortLabelAngle(location) {
    switch (location) {
        case "top":
            return -90;
        case "bottom":
            return -90;
        case "left":
            return 0;
        case "right":
            return 0;
        default:
            return 0;
    };
};

function getPortPosition(location) {
    switch (location) {
        case "top":
            return {
                name: 'line',
                args: {
                    start: { x: settings_dict['component']['labelHorizontalMargin'], y: 0 },
                    end: { x: ('calc(w - ' + settings_dict['component']['labelHorizontalMargin'] + ')'), y: 0 }
                },
            };
        case "bottom":
            return {
                name: 'line',
                args: {
                    start: { x: settings_dict['component']['labelHorizontalMargin'], y: 'calc(h)' },
                    end: { x: ('calc(w - ' + settings_dict['component']['labelHorizontalMargin'] + ')'), y: 'calc(h)' }
                },
            };
        case "left":
            return {
                name: 'line',
                args: {
                    start: { x: 0, y: settings_dict['component']['labelVerticalMargin']},
                    end: { x: 0, y: ('calc(h - ' + settings_dict['component']['labelVerticalMargin'] + ')')}
                },
            };
        case "right":
            return {
                name: 'line',
                args: {
                    start: { x: 'calc(w)', y: settings_dict['component']['labelVerticalMargin'] },
                    end: { x: 'calc(w)', y: ('calc(h - ' + settings_dict['component']['labelVerticalMargin'] + ')')}
                },
            };
        default:
            return 0;
    };
};

function measureText(text, text_size, direction) {
    var lines = text.split("\n");
    var width = 0;
    for (let line of lines) {
        var length = line.length;
        if (length > width) {
            width = length;
        };
    };
    if (direction == 'length') {
        // divide by 3 to go from font size to pxl, will have to fix
        return width * text_size * settings_dict['common']['fontLengthToPxRatio'];
    }
    else if (direction == 'height') {
        return lines.length * text_size * settings_dict['common']['fontHeightToPxRatio'];
    }
    else {
        return 0;
    }
};

// This function resizes a component based on the size of the labels and the number of ports
function resizeBasedOnLabels(element, ports_list) {
    // Largest text for each port
    let text_length_by_port = {
        'top': 0,
        'left': 0,
        'right': 0,
        'bottom': 0,
    };
    let component_port_nb = {
        'top': 0,
        'left': 0,
        'right': 0,
        'bottom': 0,
    };

    for (let port of ports_list) {
        // Check how many pins in each port
        component_port_nb[port['location']] = port['pins'].length;

        // For each port, find the longest label
        for (let pin of port['pins']) {
            label_length = measureText(pin['name'], settings_dict["component"]['pin']["fontSize"], 'length');
            if (label_length > text_length_by_port[port['name']]) {
                text_length_by_port[port['location']] = label_length;
            };
        };
    };

    // width of the component with text only
    max_label_text_width = Math.max(text_length_by_port['left'], text_length_by_port['right']);
    max_label_text_height = Math.max(text_length_by_port['top'], text_length_by_port['bottom']);

    let comp_width_by_text = element.getBBox().width + 2 * max_label_text_width;
    let comp_height_by_text = element.getBBox().height + 2 * max_label_text_height;

    element.resize(comp_width_by_text, comp_height_by_text);

    width_with_ports = 2 * settings_dict['component']['labelHorizontalMargin'] +
                        Math.max(component_port_nb['top'], component_port_nb['bottom']) * (settings_dict['component']['portPitch'] - 1);
    height_with_ports = 2 * settings_dict['component']['labelVerticalMargin'] +
                        Math.max(component_port_nb['left'], component_port_nb['right']) * (settings_dict['component']['portPitch'] - 1);

    if (width_with_ports > element.getBBox().width) {
        element.resize(width_with_ports, element.getBBox().height);
        console.log('width changed');
    };
    if (height_with_ports > element.getBBox().height) {
        element.resize(element.getBBox().width, height_with_ports);
        console.log('height changed');
    };
};


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
                targetMarker: {'type': 'none'},
            },
            z: 0
        });
        added_link.router('manhattan', {
            perpendicular: true,
            step: settings_dict['common']['gridSize'],
        });

        added_link.addTo(graph);

        var verticesTool = new joint.linkTools.Vertices();
        var segmentsTool = new joint.linkTools.Segments();
        var boundaryTool = new joint.linkTools.Boundary();

        var toolsView = new joint.dia.ToolsView({
            tools: [verticesTool, boundaryTool]
        });

        var linkView = added_link.findView(paper);
        linkView.addTools(toolsView);
        linkView.hideTools();
    }
}

function addStubs(stubs) {
    for (let stub of stubs) {
        var added_stub = new shapes.standard.Link({id: stub['uuid']});
        added_stub.prop('source', {
            id: pin_to_element_association[stub['source']],
            port: stub['source']});
        if (stub['position']) {
            added_stub.prop('target', stub['position']);
        } else {
            added_stub.prop('target', { x: 10, y: 10 });
        }
        added_stub.router('manhattan', {
            startDirections: [stub['direction']],
            endDirections: [opposite_direction[stub['direction']]],
            perpendicular: true,
            step: settings_dict['common']['gridSize'],
        });
        added_stub.attr('root/title', 'joint.shapes.standard.Link');
        added_stub.attr({
            line: {
                'stroke': settings_dict['link']['color'],
                'stroke-width': settings_dict['link']['strokeWidth'],
                //targetMarker: {'type': 'none'},
            },
            z: 0
        });
        let label_offset;
        (stub['direction'] == 'bottom') ? label_offset = 10 : label_offset = -10;
        added_stub.appendLabel({
            attrs: {
                text: {
                    text: stub['name'],
                    fontFamily: settings_dict['common']['fontFamily'],
                    fontSize: settings_dict['stubs']['fontSize'],
                }
            },
            position: {
                distance: 1,
                offset: {
                    x: 0,
                    y: label_offset
                },
                angle: 0,
                args: {
                    keepGradient: false
                }
            }
        });
        added_stub.addTo(graph);
    };
}

function getElementTitle(element) {
    if (element['instance_of'] != null) {
        return`${element['name']} \n(${element['instance_of']})`;
    } else {
        return element['name'];;
    }
}

function addPorts(element) {

}

function createComponent(element, parent) {
    let title = getElementTitle(element);
    comp_width = measureText(title, settings_dict['component']['pin']['fontSize'], 'length') + 2 * settings_dict['component']['titleMargin'];
    comp_height = measureText(title, settings_dict['component']['pin']['fontSize'], 'height') + 2 * settings_dict['component']['titleMargin'];
    const component = new AtoComponent({
        id: element['uuid'],
        size: { width: comp_width,
                height: comp_height},
        attrs: {
            label: {
                text: title,
            }
        }
    });

    //resizeBasedOnLabels(component, ports_dict);
    //resizeBasedOnPorts(component, ports_dict);

    component.addTo(graph);

    if (parent) {
        addElementToElement(component, parent);
    }

    return component;
}

function createBlock(element, parent) {
    let title = getElementTitle(element);
    const block = new AtoBlock({
        id: element['uuid'],
        attrs: {
            label: {
                text: title,
            }
        }
    });

    //addPortsAndPins(block, ports_dict);

    block.addTo(graph);

    if (parent) {
        addElementToElement(block, parent);
    }

    return block;
}

function addElementToElement(block_to_add, to_block) {
    to_block.embed(block_to_add);
}

function returnConfigFileName(string) {
    if (string) {
        const [file, module] = string.split(":");
        return {"file": file, "module": module}
    }
    else return null;
}

function getElementPosition(element_name, config) {
    let position = {'x': 10, 'y': 10};
    if (config && element_name in config) {
        position = config[element_name]['position'];
    }
    return position;
}

async function generateJointjsGraph(circuit, parent = null) {
    let jointJSCircuit = [];

    for (let element of circuit) {
        var created_element = null;

        if (element['type'] == 'component') {
            joint_object = createComponent(element, parent);
            element['jointObject'] = joint_object;
        }

        // If it is a block, create it and instantiate the contents within it
        else if (element['type'] == 'module') {
            // Create the module
            created_element = createBlock(element, parent);
            element['jointObject'] = created_element;


            // Call the function recursively on children
            await generateJointjsGraph(element['blocks'], created_element);

            //addLinks(element['links']);
            //addStubs(element['stubs']);
            //created_element.fitAncestorElements();

            //applyConfig(element, blocks_config);
        }

        else if (element['type'] == 'file') {
            //let file = getElementTitle(element);
            await generateJointjsGraph(element['blocks']);
        }

        else {
            // raise an error because we don't know what to do with this element
            // TODO: raise an error
            console.log('Unknown element type: '+ element['type']);
        }
    }
}

async function populateConfigFromBackend(circuit_dict, parent_path = null) {
    let populated_circuit = [];
    let path = "";

    for (let element of circuit_dict) {
        path = element['name']
        if (parent_path !== null){
            path = parent_path + '/' + path;
        };
        if (element['type'] == 'component') {
            if (element['instance_of'] !== null) {
                config_location_name = returnConfigFileName(element['instance_of']);
                const config = await loadFileConfig(config_location_name['file']);
                element['config'] = null;
                if (config !== null) {
                    element['config'] = config[config_location_name['module']];
                }
            }
        }
        if (element['type'] == 'module' || element['type'] == 'file') {
            if (element['instance_of'] !== null) {
                config_location_name = returnConfigFileName(element['instance_of']);
                const config = await loadFileConfig(config_location_name['file']);
                element['config'] = null;
                if (config !== null) {
                    element['config'] = config[config_location_name['module']];
                }
            }
            element['blocks'] = await populateConfigFromBackend(element['blocks'], path);
        }
        element['uuid'] = path;
        populated_circuit.push(element);
    }
    return populated_circuit;
}

function applyConfig(element, config) {
    block_position = null;
    try {
        block_position = config['blocks_positions'];
    }
    catch(err) {
        console.log('Block position not provided for ' + element['name']);
    }
    let position = getElementPosition(element['name'], block_position);
    // Deep setting ensures that the element is placed relative to all parents
    element['jointObject'].position(position['x'], position['y'], { deep: true });
}

const graph = new dia.Graph({}, { cellNamespace });
const paper = new joint.dia.Paper({
    el: document.getElementById('atopilePaper'),
    model: graph,
    width: '100%',
    height: '100%',
    gridSize: settings_dict['common']['gridSize'],
    drawGrid: true,
    background: {
        color: settings_dict["common"]["backgroundColor"]
    },
    interactive: true,
    cellViewNamespace: cellNamespace,
});

function fill_paper() {
    paper.setDimensions(window.innerWidth, window.innerHeight);
}

window.onload = fill_paper;
window.onresize = fill_paper;

let pin_to_element_association = {};

paper.on('link:mouseenter', function(linkView) {
    linkView.showTools();
    linkView.highlight();
});

paper.on('link:mouseleave', function(linkView) {
    linkView.hideTools();
    linkView.unhighlight();
});

paper.on('cell:pointerup', function(cell, evt, x, y) {
    let requestOptions = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: {}
    };
    if (cell.model instanceof AtoComponent) {
        requestOptions.body = JSON.stringify({
            id: cell.model.attributes.id,
            x: cell.model.attributes.position.x,
            y: cell.model.attributes.position.y,
        });
        fetch('/api/view/move', requestOptions);
    } else if (cell.model instanceof shapes.standard.Link) {
        requestOptions.body = JSON.stringify({
            id: cell.model.attributes.id,
            x: cell.targetPoint.x,
            y: cell.targetPoint.y,
        });
        fetch('/api/view/move', requestOptions);
    }
});

graph.on('change:position', function(cell) {
    // `fitParent()` method is defined at `joint.shapes.container.Base` in `./joint.shapes.container.js`
    //cell.fitAncestorElements();
});

// Fetch a file visual config from the server
async function loadFileConfig(file_name) {
    //const response = await fetch('/api/view');

    // Strip .ato from the name
    let striped_file_name = file_name.replace(".ato", "");
    let address = "/static/" + striped_file_name + '_config.json';
    let response;
    try {
        response = await fetch(address);
    } catch (error) {
        console.log('Could not fetch config ', error);
    }

    if (response.ok) {
        return response.json();
    } else {
        console.log(`HTTP Response Code: ${response?.status}`)
        return null;
    }
}

// Fetch a circuit dict from the server
async function loadCircuit() {
    //const response = await fetch('/api/view');
    const response = await fetch('/static/circuit2.json');
    const circuit_data = await response.json();

    let config_populated_circuit = await populateConfigFromBackend(circuit_data);
    console.log(config_populated_circuit);
    generateJointjsGraph(config_populated_circuit);
}

loadCircuit();
