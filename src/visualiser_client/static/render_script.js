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

function customAnchor(view, magnet, ref, opt, endType, linkView) {
    const elBBox = view.model.getBBox();
    const magnetCenter = view.getNodeBBox(magnet).center();
    const side = elBBox.sideNearestToPoint(magnetCenter);
    let dx = 0;
    let dy = 0;
    const length = ('length' in opt) ? opt.length : 20;
    switch (side) {
        case 'left':
        dx = -length;
        break;
        case 'right':
        dx = length;
        break;
        case 'top':
        dy = -length;
        break;
        case 'bottom':
        dy = length;
        break;

    }
    return joint.anchors.center.call(this, view, magnet, ref, {
      ...opt,
      dx,
      dy
    }, endType, linkView);
}

// Base class for the visual elements
class AtoElement extends dia.Element {
    defaults() {
        return {
            ...super.defaults,
        };
    }

    addPortWithPins(port_group_name, port_location, pin_list) {
        let port_label_position = getPortLabelPosition(port_location);
        let port_anchor = getPortLabelAnchor(port_location);
        let port_angle = getPortLabelAngle(port_location);
        let port_position = getPortPosition(port_location);

        let port_group = {};

        port_group[port_group_name] = {
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

        // Add the ports list to the element
        this.prop({"ports": { "groups": port_group}});

        // While we are creating the port, add the pins in the element
        for (let pin of pin_list) {
            //console.log('pin uuid: ', pin['path']);
            //console.log('pin name: ', pin['name']);
            this.addPort(createPort(pin['path'], pin['name'], port_group_name, port_anchor, true));
        }
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

    applyParentAttrs(attrs) {
        if ('position' in attrs) {
            // Deep setting ensures that the element is placed relative to all parents
            this.position(attrs['position']['x'], attrs['position']['y'], { deep: true });
        }
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
}

// Class for a block
// For the moment, blocks and components are separate.
// We might want to combine them in the future.
class AtoBlock extends AtoElement {
    defaults() {
        return {
            ...super.defaults(),
            type: "AtoComponent",
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
                    fill: "black",
                    textVerticalAnchor: "top",
                    fontSize: settings_dict['block']['label']['fontSize'],
                    fontWeight: settings_dict["block"]['label']["fontWeight"],
                    textAnchor: "start",
                    fontFamily: settings_dict["common"]["fontFamily"],
                    x: 8,
                    y: 8
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

    updateChildrenVisibility() {
        const collapsed = this.isCollapsed();
        this.getEmbeddedCells().forEach((child) => child.set("hidden", collapsed));
    }
}


const cellNamespace = {
    ...shapes,
    AtoElement,
    AtoComponent,
    AtoBlock
};

function createPort(uuid, port_name, port_group_name, port_anchor) {
    return {
        id: uuid,
        group: port_group_name,
        attrs: {
            label: {
                text: port_name,
                fontFamily: settings_dict['common']['fontFamily'],
                fontSize: settings_dict['component']['pin']['fontSize'],
                fontWeight: settings_dict["component"]['pin']["fontWeight"],
                textAnchor: port_anchor,
            },
        },
        // markup: '<circle id="Oval" stroke="#000000" fill="#FFFFFF" cx="0" cy="0" r="2"/>'
    }
}

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


function addLinks(links, current_path) {
    for (let link of links) {
        let source_path = concatenatePathAndName(current_path, link['source']);
        let target_path = concatenatePathAndName(current_path, link['target']);
        let source = popLastPathElementFromPath(source_path);
        let target = popLastPathElementFromPath(target_path);
        let source_pin = source['pin'];
        let target_pin = target['pin'];
        let source_block = source['path'];
        let target_block = target['path'];
        console.log('Creating a link');
        console.log('source block ' + source_block + " pin: " + source_path );
        console.log('source block ' + source_block + " pin: " + source_path );

        let added_link = new shapes.standard.Link({
            source: {
                id: source_block,
                port: source_path,
                anchor: {
                    name: 'center'
                }
            },
                target: {
                id: source_block,
                port: source_path,
                anchor: {
                    name: 'customAnchor'
                },
                connectionPoint: {
                    name: 'anchor'
                }
            }
        });
        console.log(added_link);

        graph.addCell(added_link);
    }
    // for (let link of links) {
    //     var added_link = new shapes.standard.Link({
    //         source: {
    //             id: pin_to_element_association[link['source']],
    //             port: link['source']
    //         },
    //         target: {
    //             id: pin_to_element_association[link['target']],
    //             port: link['target']
    //         }
    //     });
    //     added_link.attr({
    //         line: {
    //             'stroke': settings_dict['link']['color'],
    //             'stroke-width': settings_dict['link']['strokeWidth'],
    //             targetMarker: {'type': 'none'},
    //         },
    //         z: 0
    //     });
    //     added_link.router('manhattan', {
    //         perpendicular: true,
    //         step: settings_dict['common']['gridSize'],
    //     });

    //     added_link.addTo(graph);

    //     var verticesTool = new joint.linkTools.Vertices();
    //     var segmentsTool = new joint.linkTools.Segments();
    //     var boundaryTool = new joint.linkTools.Boundary();

    //     var toolsView = new joint.dia.ToolsView({
    //         tools: [verticesTool, boundaryTool]
    //     });

    //     var linkView = added_link.findView(paper);
    //     linkView.addTools(toolsView);
    //     linkView.hideTools();
    // }
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

function addPins(jointJSObject, element, path) {
    console.log('add pins with path ', path);
    // Create the default port location
    let ports_to_add = {};
    ports_to_add['default'] = {
        "location": "top",
        "pins": []
    };
    // Create the ports that are defined in the config
    for (let port of element['config']['ports']) {
        ports_to_add[port['name']] = {
            "location": port["location"],
            "pins": []
        }
    }

    let config_found;
    console.log(element['name']);
    console.log(ports_to_add);
    for (let circuit_pin of element['pins']) {
        // Let's all pins to their respective port
        let pin_to_add = circuit_pin;
        pin_to_add['path'] = concatenatePathAndName(path, pin_to_add['name']);
        config_found = false;

        for (let config_pin of element['config']['pins']) {
            // If a port is defined, add it to it designated port
            if (pin_to_add['name'] == config_pin['name']) {
                console.log('adding a pin');
                console.log(pin_to_add);
                ports_to_add[config_pin['port']]['pins'].push(pin_to_add);
                config_found = true;
            }
        }
        // If no port is defined, add it to the default port
        if (!config_found) {
            ports_to_add['default']['pins'].push(pin_to_add);
        }
    }

    for (let port in ports_to_add) {
        if (ports_to_add[port]['pins'].length > 0) {
            jointJSObject.addPortWithPins(port, ports_to_add[port]['location'], ports_to_add[port]['pins']);
        }
    }
}

function createComponent(element, parent, path) {
    console.log("Create comp: ", path);
    let title = getElementTitle(element);
    comp_width = measureText(title, settings_dict['component']['pin']['fontSize'], 'length') + 2 * settings_dict['component']['titleMargin'];
    comp_height = measureText(title, settings_dict['component']['pin']['fontSize'], 'height') + 2 * settings_dict['component']['titleMargin'];
    var component = new AtoComponent({
        id: path,
        size: { width: comp_width,
                height: comp_height},
        attrs: {
            label: {
                text: title,
            }
        }
    });


    addPins(component, element, path);

    //resizeBasedOnLabels(component, ports_dict);
    //resizeBasedOnPorts(component, ports_dict);

    component.addTo(graph);

    if (parent) {
        addElementToElement(component, parent);
    }

    return component;
}

function createBlock(element, parent, path) {
    let title = getElementTitle(element);
    const block = new AtoBlock({
        id: path,
        attrs: {
            label: {
                text: title,
            }
        }
    });

    addPins(block, element, path);

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

function concatenatePathAndName(path, name) {
    if (path == null) {
        return name + ':'
    }
    else if (path.slice(-1) == ':') {
        return path + name;
    }
    else {
        return path + '.' + name;
    }
}

function popLastPathElementFromPath(path) {
    const blocks = path.split(".");
    const path_blocks = blocks.slice(0, blocks.length - 1);
    const remaining_path = path_blocks.join('.')
    const pin = blocks[blocks.length - 1];
    return {'path': remaining_path, 'pin': pin};
}

function getElementPosition(element_name, config) {
    let position = {'x': 10, 'y': 10};
    if (config && element_name in config) {
        position = config[element_name]['position'];
    }
    return position;
}

function applyParentConfig(element, child_attrs) {
    if (child_attrs !== null && Object.keys(child_attrs).length > 0) {
        for (let attrs in child_attrs) {
            if (attrs == element['name']) {
                element['jointObject'].applyParentAttrs(child_attrs[attrs]);
            }
        }
    }
}

async function generateJointjsGraph(circuit, path = null, parent = null, child_attrs = null) {
    let downstream_path;
    console.log('the current path is: ', path);

    for (let element of circuit) {
        var joint_object = null;

        if (element['type'] == 'component') {
            downstream_path = concatenatePathAndName(path, element['name']);
            joint_object = createComponent(element, parent, downstream_path);
            element['jointObject'] = joint_object;
            if (parent) {
                addElementToElement(joint_object, parent);
            }
            applyParentConfig(element, child_attrs);
        }

        // If it is a block, create it and instantiate the contents within it
        else if (element['type'] == 'module') {
            downstream_path = concatenatePathAndName(path, element['name']);
            // Create the module
            joint_object = createBlock(element, parent, downstream_path);
            element['jointObject'] = joint_object;
            if (parent) {
                addElementToElement(joint_object, parent);
            }

            // Call the function recursively on children
            await generateJointjsGraph(element['blocks'], downstream_path, joint_object, element['config']['child_attrs']);

            addLinks(element['links'], path)

            applyParentConfig(element, child_attrs);
            //addLinks(element['links']);
            //addStubs(element['stubs']);
            //created_element.fitAncestorElements();

            //applyConfig(element, blocks_config);
        }

        else if (element['type'] == 'file') {
            downstream_path = concatenatePathAndName(path, element['name']);
            await generateJointjsGraph(element['blocks'], downstream_path);
        }

        else {
            // raise an error because we don't know what to do with this element
            // TODO: raise an error
            console.log('Unknown element type: ' + element['type']);
        }
    }
}

let default_config = {
    "ports": [],
    "pins": [],
    'child_attrs': []
}

async function populateConfigFromBackend(circuit_dict) {
    let populated_circuit = [];

    for (let element of circuit_dict) {
        if (element['type'] == 'component') {
            if (element['instance_of'] !== null) {
                config_location_name = returnConfigFileName(element['instance_of']);
                const config = await loadFileConfig(config_location_name['file']);
                element['config'] = default_config;
                if (config !== null) {
                    element['config'] = config[config_location_name['module']];
                }
            }
        }
        if (element['type'] == 'module' || element['type'] == 'file') {
            if (element['instance_of'] !== null) {
                config_location_name = returnConfigFileName(element['instance_of']);
                const config = await loadFileConfig(config_location_name['file']);
                element['config'] = default_config;
                if (config !== null) {
                    element['config'] = config[config_location_name['module']];
                }
            }
            element['blocks'] = await populateConfigFromBackend(element['blocks']);
        }
        populated_circuit.push(element);
    }
    return populated_circuit;
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
    snapLinks: true,
    linkPinning: false,
    magnetThreshold: 'onleave',
    cellViewNamespace: cellNamespace,
    anchorNamespace: {
        ...joint.anchors,
        customAnchor
    }
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
    cell.fitAncestorElements();
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
