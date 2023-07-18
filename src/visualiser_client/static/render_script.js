// TODO: the root cell ID has a colon in it, which there shouldn't be

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
        labelHorizontalMargin: 30,
        labelVerticalMargin: 4,
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
        fontSize: 8,
    }
}

function customAnchor(view, magnet, ref, opt, endType, linkView) {
    const elBBox = view.model.getBBox();
    const magnetCenter = view.getNodeBBox(magnet).center();
    const side = elBBox.sideNearestToPoint(magnetCenter);
    let dx = 0;
    let dy = 0;
    const length = ('length' in opt) ? opt.length : 30;
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
            instance_name: null,
            config_origin_filename: null,
            config_origin_module: [],
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
            this.addPort(createPort(pin['path'], pin['name'], port_group_name, port_anchor, true));
        }
    }

    resizeBasedOnContent() {
        let ports = this.getPorts();
        if (ports) {
            let port_buckets = {
                "top": this.getGroupPorts('top'),
                "bottom": this.getGroupPorts('bottom'),
                "left": this.getGroupPorts('left'),
                "right": this.getGroupPorts('right')
            };
            let ports_text_length = {
                "top": "",
                "bottom": "",
                "left": "",
                "right": ""
            };
            let dim_from_text = {
                "height": 0,
                "width": 0
            };
            let dim_from_ports = {
                "height": 0,
                "width": 0
            }

            // Extract the longest port label from each bucket
            for (let port_bucket in port_buckets) {
                if (port_buckets[port_bucket].length) {
                    for (let port of port_buckets[port_bucket]) {
                        if (port["attrs"]["label"]["text"].length > ports_text_length[port_bucket].length) {
                            ports_text_length[port_bucket] = port["attrs"]["label"]["text"];
                        }
                    }
                }
            }

            dim_from_text['height'] = 2 * (Math.max(measureText(ports_text_length['top'], settings_dict['component']['fontSize'], "length"), measureText(ports_text_length['bottom'], settings_dict['component']['fontSize'], "length")));
            dim_from_text['height'] += measureText(this['attributes']['attrs']['label']['text'], settings_dict['component']['fontSize'], "height");
            dim_from_text['height'] += settings_dict['component']['labelVerticalMargin'] * 2;
            dim_from_text['width'] = 2 * (Math.max(measureText(ports_text_length['right'], settings_dict['component']['fontSize'], "length"), measureText(ports_text_length['left'], settings_dict['component']['fontSize'], "length")));
            dim_from_text['width'] += measureText(this['attributes']['attrs']['label']['text'], settings_dict['component']['fontSize'], "length");

            dim_from_ports['height'] = (Math.max(port_buckets['right'].length, port_buckets['left'].length) + 1) * settings_dict['component']['portPitch'];
            dim_from_ports['width'] = (Math.max(port_buckets['top'].length, port_buckets['bottom'].length) - 1) * settings_dict['component']['portPitch'];
            dim_from_ports['width'] += 2 * settings_dict['component']['labelHorizontalMargin'];
            // Feature does not work without moveable ports
            // if (port_buckets['right'].length != 0 || port_buckets['left'].length != 0) {
            //     if (port_buckets['top'].length != 0 || port_buckets['bottom'].length != 0) {
            //         dim_from_ports['width'] += 2 * settings_dict['component']['labelHorizontalMargin'];
            //     }
            // }

            this.resize(Math.max(dim_from_text['width'], dim_from_ports['width']), Math.max(dim_from_text['height'], dim_from_ports['height']));
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
            return [0, 5];
        case "bottom":
            return [0, -5];
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

// Definitely need to update this garbage at some point
function measureText(text, text_size, direction) {
    var string = text + '';
    var lines = string.split("\n");
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

function addStub(block_id, port_id, label) {
    let added_stub = new shapes.standard.Link({
        source: {
            id: block_id,
            port: port_id,
            anchor: {
                name: 'center'
            }
        },
            target: {
            id: block_id,
            port: port_id,
            anchor: {
                name: 'customAnchor'
            },
            connectionPoint: {
                name: 'anchor'
            }
        }
    });
    added_stub.attr({
        line: {
            'stroke': settings_dict['link']['color'],
            'stroke-width': settings_dict['link']['strokeWidth'],
            targetMarker: {'type': 'none'},
        },
        z: 0,
    });
    added_stub.appendLabel({
        attrs: {
            text: {
                text: label,
                fontFamily: settings_dict['common']['fontFamily'],
                fontSize: settings_dict['stubs']['fontSize'],
                //textVerticalAnchor: "middle",
                textAnchor: "middle",
            }
        },
        position: {
            distance: .9,
            offset: -5,
            angle: 0,
            args: {
                keepGradient: true,
                ensureLegibility: true,
            }
        }
    });
    graph.addCell(added_stub);
}

function addLink(source_block_id, source_port_id, target_block_id, target_port_id) {
    var added_link = new shapes.standard.Link({
        source: {
            id: source_block_id,
            port: source_port_id
        },
        target: {
            id: target_block_id,
            port: target_port_id
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
}


function addLinks(element, current_path) {
    for (let link of element['links']) {
        // Add the block (if there is one) and port to the path
        let source_path = concatenatePathAndName(current_path, link['source']);
        let target_path = concatenatePathAndName(current_path, link['target']);
        // Remove the port from the path to get the block path
        let source = popLastPathElementFromPath(source_path);
        let target = popLastPathElementFromPath(target_path);
        let source_block = source['path'];
        let target_block = target['path'];

        let is_stub = false;
        for (let link_config of ((element.config || {}).signals || [])) {
            if (link_config['name'] == link['name'] && link_config['is_stub']) {
                is_stub = true;
                // if not a module
                if (current_path.length != source_block.length) {
                    addStub(source_block, source_path, link['name']);
                }
                // if not a module
                if (current_path.length != target_block.length) {
                    addStub(target_block, target_path, link['name']);
                }
            }
        }
        if (!is_stub) {
            addLink(source_block, source_path, target_block, target_path);
        }
    }
}

function getElementTitle(element) {
    if (element['instance_of'] != null) {
        return`${element['name']} \n(${popLastPathElementFromPath(element['instance_of']).name})`;
    } else {
        return element['name'];;
    }
}

function addPins(jointJSObject, element, path) {
    // Create the default port location
    let ports_to_add = {};

    // Create the ports that are defined in the config
    for (let port of ((element.config || {}).ports || [])) {
        ports_to_add[(port.name || "top")] = {
            "location": (port.location || "top"),
            "pins": []
        }
    }

    let config_found;
    for (let pin_to_add of element['pins']) {

        pin_to_add['path'] = concatenatePathAndName(path, pin_to_add['name']);

        config_found = false;
        for (let config_pin of ((element.config || {}).pins || [])) {
            // If a port is defined, add it to it designated port
            if (pin_to_add['name'] == config_pin['name']) {
                ports_to_add[config_pin['port']]['pins'].push(pin_to_add);
                config_found = true;
            }
        }
        // If no port is defined, add it to the default port
        if (!config_found) {
            if (!ports_to_add['top']) ports_to_add['top'] = {"location": "top", "pins": []};
            ports_to_add['top']['pins'].push(pin_to_add);
        }
    }

    for (let port in ports_to_add) {
        if (ports_to_add[port]['pins'].length > 0) {
            jointJSObject.addPortWithPins(port, ports_to_add[port]['location'], ports_to_add[port]['pins']);
        }
    }
}

function createComponent(element, parent, path) {
    let title = getElementTitle(element);
    comp_width = measureText(title, settings_dict['component']['pin']['fontSize'], 'length') + 2 * settings_dict['component']['titleMargin'];
    comp_height = measureText(title, settings_dict['component']['pin']['fontSize'], 'height') + 2 * settings_dict['component']['titleMargin'];
    var component = new AtoComponent({
        id: path,
        instance_name: element['name'],
        size: { width: comp_width,
                height: comp_height},
        attrs: {
            label: {
                text: title,
            }
        },
        config_origin_filename: element.config_origin_filename,
        config_origin_module: element.config_origin_module,
    });

    addPins(component, element, path);
    component.resizeBasedOnContent();
    component.addTo(graph);

    if (parent) {
        addElementToElement(component, parent);
    }

    return component;
}

function createBlock(element, parent, path) {
    let title = getElementTitle(element);
    let block = new AtoBlock({
        id: path,
        instance_name: element['name'],
        size: {
            width: 200,
            height: 100
        },
        attrs: {
            label: {
                text: title,
            }
        },
        config_origin_filename: element.config_origin_filename,
        config_origin_module: element.config_origin_module,
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
    // Split the file name and the blocks
    const file_block = path.split(":");
    const file = file_block[0];
    // Split the blocks
    const blocks = file_block[1].split(".");
    const path_blocks = blocks.slice(0, blocks.length - 1);
    const remaining_path = file + ':' + path_blocks.join('.')
    const name = blocks[blocks.length - 1];
    return {'file': file, 'path': remaining_path, 'name': name};
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

async function generateJointjsGraph(circuit, max_depth, current_depth = 0, path = null, parent = null, child_attrs = null) {
    let downstream_path;
    let new_depth = current_depth + 1;

    if (current_depth <= max_depth) {
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
                if (await generateJointjsGraph(element['blocks'], max_depth, new_depth, downstream_path, joint_object, element['config']['child_attrs'])) {
                    addLinks(element, downstream_path)
                    applyParentConfig(element, child_attrs);
                }

                // FIXME:
                // Position the root element in the middle of the screen
                if (current_depth == 0) {
                    let paperSize = paper.getComputedSize();
                    let rootSize = joint_object.size();

                    // Calculate the position for the center of the paper.
                    let posX = (paperSize.width / 2) - (rootSize.width / 2);
                    let posY = (paperSize.height / 2) - (rootSize.height / 2);

                    // Position the rectangle in the center of the paper.
                    joint_object.position(posX, posY);
                    // TODO: bring the other content with it
                }
            }

            else if (element['type'] == 'file') {
                downstream_path = concatenatePathAndName(path, element['name']);
                await generateJointjsGraph(element['blocks'], max_depth, new_depth, downstream_path);
            }

            else {
                // raise an error because we don't know what to do with this element
                // TODO: raise an error
                console.log('Unknown element type: ' + element['type']);
            }
        }
        return true;
    }
    else {
        return false;
    }
}

async function populateConfigFromBackend(circuit_dict, file_name = null) {
    let populated_circuit = [];

    for (let element of circuit_dict) {
        if (element.type == 'component') {
            if (element.instance_of !== null) {
                config_location_name = returnConfigFileName(element.instance_of);
                element.config_origin_filename = getConfigFilenameFromAto(config_location_name.file);
                element.config_origin_module = config_location_name.module;
                const config = await loadFileConfig(config_location_name.file);
                element['config'] = config[config_location_name.module] || {};
            }
        }
        else if (element.type == 'module') {
            let config = null;
            element.config = {};
            if (element.instance_of !== null) {
                config_location_name = returnConfigFileName(element.instance_of);
                element.config_origin_filename = getConfigFilenameFromAto(config_location_name.file);
                element.config_origin_module = config_location_name.module;
                config = await loadFileConfig(config_location_name.file);
            }

            if (config) {
                if (Object.keys(config).length !== 0) {
                    if (config.hasOwnProperty(config_location_name['module'])) {
                        element['config'] = config[config_location_name['module']];
                    }
                }
            }
            element['blocks'] = await populateConfigFromBackend(element['blocks']);
        }
        else if (element['type'] == 'file') {
            // If file, the following block will not be an instance, so it needs to know it's parent file
            // to fetch the config
            element['blocks'] = await populateConfigFromBackend(element['blocks'], element['name']);
        }
        else {
            console.log("unknown block type");
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

graph.on('change:position', function(cell) {
    // `fitParent()` method is defined at `joint.shapes.container.Base` in `./joint.shapes.container.js`
    cell.fitAncestorElements();
});

function getConfigFilenameFromAto(ato_file_name) {
    // Strip .ato from the name
    let striped_file_name = ato_file_name.replace(".ato", "");
    return  striped_file_name + '.vis.json';
}

// Fetch a file visual config from the server
async function loadFileConfig(file_name) {
    let address = "/api/config/" + getConfigFilenameFromAto(file_name);
    //address = "/api/circuit/bike_light.ato:BikeLight";
    let response;
    try {
        response = await fetch(address);
    } catch (error) {
        console.log('Could not fetch config ', error);
    }

    if (response.ok) {
        return await response.json();
    } else {
        console.log(`HTTP Response Code: ${response?.status}`)
        return null;
    }
}

// Fetch a circuit dict from the server
async function loadCircuit() {
    const urlParams = new URLSearchParams(window.location.search);
    const response = await fetch('/api/circuit/' + urlParams.get('circuit'));
    const circuit_data = await response.json();
    console.log("data received from backend")
    console.log(circuit_data);

    let config_populated_circuit = await populateConfigFromBackend([circuit_data]);
    console.log(config_populated_circuit);
    generateJointjsGraph(config_populated_circuit, 1);
}

// flag to help rate limit calls to savePositions
var stuff_has_moved = false;

paper.on('cell:pointerup', function(cell, evt, x, y) {
    if (cell.model instanceof AtoComponent || cell.model instanceof AtoBlock) {
        stuff_has_moved = true;
    }
});

function savePositions() {
    let requests_to_make = {};

    graph.getCells().forEach(function(cell) {
        if (cell instanceof AtoComponent || cell instanceof AtoBlock) {
            console.log(cell.id);

            let parent = cell.getParentCell();
            if (!parent) return; // skip the root element

            let origin_file = parent.attributes.config_origin_filename;
            let origin_module = parent.attributes.config_origin_module;
            let instance_name = cell.attributes.instance_name;

            if (!requests_to_make[origin_file]) requests_to_make[origin_file] = {};
            if (!requests_to_make[origin_file][origin_module]) requests_to_make[origin_file][origin_module] = {"child_attrs": {}};
            requests_to_make[origin_file][origin_module]["child_attrs"][instance_name] = {
                "position": {
                    x: cell.attributes.position.x - parent.attributes.position.x,
                    y: cell.attributes.position.y - parent.attributes.position.y,
                }
            };
        }
    });

    for (let origin_file in requests_to_make) {
        let requestOptions = {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requests_to_make[origin_file])
        };
        fetch('/api/config/' + origin_file, requestOptions);
    }

    // reset the flag
    stuff_has_moved = false;
}

// rate limit the calls to savePositions
setInterval(function() {
    if (stuff_has_moved) {
        console.log("saving positions");
        savePositions();
    }
}, 1000);

loadCircuit();
