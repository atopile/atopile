import { shapes, util, dia, anchors } from 'jointjs';

import { measureText, normalizeDimensionToGrid, isIterable } from './utils';

import { settings_dict } from './viewer_settings';

// Base class for the visual elements
export class AtoElement extends dia.Element {
    defaults() {
        return {
            ...super.defaults,
            instance_name: null,
        };
    }

    addPortSingle(path, name, port_group_name) {
        let port_anchor = getPortLabelAnchor(port_group_name);
        this.addPort(createPort(path, name, port_group_name, port_anchor));
    }

    addPortGroup(port_group_name, port_location, port_offset, max_length) {
        let port_label_position = getPortLabelPosition(port_location);
        let port_angle = getPortLabelAngle(port_location);
        let port_list = this.getGroupPorts(port_location);
        let port_position = getPortPosition(port_location, port_list, port_offset, max_length);

        let port_group = {};

        port_group[port_group_name] = {
            position: port_position,
            attrs: {
                portBody: {
                    magnet: true,
                    r: 2,
                    fill: '#FFFFFF',
                    stroke: '#023047',
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
        this.prop({ "ports": { "groups": port_group } });
    }

    createDefaultPorts() {
        this.addPortGroup('top', 'top');
        this.addPortGroup('left', 'left');
        this.addPortGroup('right', 'right');
        this.addPortGroup('bottom', 'bottom');
    }
    // TODO: need to change to add port and add pins in port
    addPortGroupWithPorts(port_group_name, port_location, pin_list) {
        this.addPortGroup(port_group_name, port_location);

        // While we are creating the port, add the pins in the element
        for (let pin of pin_list) {
            this.addPortSingle(pin['path'], pin['name'], port_group_name);
        }
    }

    resizeBasedOnContent() {
        // There are 5 rectangles that define the size of an element.
        // The four side rectangles contain the ports. The center one contains the name.
        // The left and right rectangles take the full height of the element.
        // The width of the element is equal to the left and right width + the widest of the top or bottom rectangle.
        var top_port_dim = {
            "height": 0,
            "width": 0
        };
        var bottom_port_dim = {
            "height": 0,
            "width": 0
        };
        var left_port_dim = {
            "height": 0,
            "width": 0
        };
        var right_port_dim = {
            "height": 0,
            "width": 0
        };
        var center_name_dim = {
            "height": 0,
            "width": 0
        };

        // Variable for the top and bottom ports offset from left and right edge for port creation
        var max_left_right_port_width = 0;
        // Variable used to center the top and bottom port in the center of the component
        var max_horizontal_width = 0;

        // Compute the center rectangle dimension
        center_name_dim['height'] = measureText(this['attributes']['attrs']['label']['text'], settings_dict['component']['fontSize'], "height");
        center_name_dim['height'] += settings_dict['component']['titleMargin'];
        center_name_dim['width'] = measureText(this['attributes']['attrs']['label']['text'], settings_dict['component']['fontSize'], "length");
        center_name_dim['width'] += settings_dict['component']['titleMargin'];

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

            top_port_dim['height'] = measureText(ports_text_length['top'], settings_dict['component']['fontSize'], "length") + settings_dict['component']['portLabelToBorderGap'];
            top_port_dim['width'] = (port_buckets['top'].length - 1) * settings_dict['component']['portPitch'] + settings_dict['component']['labelHorizontalMargin'];

            bottom_port_dim['height'] = measureText(ports_text_length['bottom'], settings_dict['component']['fontSize'], "length") + settings_dict['component']['portLabelToBorderGap'];
            bottom_port_dim['width'] = (port_buckets['bottom'].length - 1) * settings_dict['component']['portPitch'] + settings_dict['component']['labelHorizontalMargin'];

            // + 1 since we need a margin at the top and bottom
            left_port_dim['height'] = (port_buckets['left'].length) * settings_dict['component']['portPitch'];
            left_port_dim['width'] = measureText(ports_text_length['left'], settings_dict['component']['fontSize'], "length") + settings_dict['component']['portLabelToBorderGap'];

            right_port_dim['height'] = (port_buckets['right'].length) * settings_dict['component']['portPitch'];
            right_port_dim['width'] = measureText(ports_text_length['right'], settings_dict['component']['fontSize'], "length") + settings_dict['component']['portLabelToBorderGap'];
        }
        //TODO: fix this function when ports are added automatically
        let final_dim = {
            "height": 0,
            "width": 0
        };

        max_left_right_port_width = Math.max(right_port_dim['width'], left_port_dim['width']);
        max_horizontal_width = Math.max(top_port_dim['width'], bottom_port_dim['width'], center_name_dim['width']);
        var max_height = Math.max(right_port_dim['height'], left_port_dim['height'], (2 * Math.max(top_port_dim['height'], bottom_port_dim['height']) + center_name_dim['height']));

        // The width is the widest between the top, center and bottom
        final_dim['width'] = max_horizontal_width;
        final_dim['width'] += 2 * max_left_right_port_width;
        final_dim['width'] = normalizeDimensionToGrid(final_dim['width'], settings_dict['common']['gridSize']);

        final_dim['height'] = max_height;
        final_dim['height'] = normalizeDimensionToGrid(final_dim['height'], settings_dict['common']['gridSize']);

        this.resize(final_dim['width'], final_dim['height']);

        //FIXME: currently just adding a port everywhere to resize the ports
        this.addPortGroup('top', 'top', max_left_right_port_width, max_horizontal_width);
        this.addPortGroup('left', 'left', 0, max_height);
        this.addPortGroup('right', 'right', 0, max_height);
        this.addPortGroup('bottom', 'bottom', max_left_right_port_width, max_horizontal_width);
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
export class AtoComponent extends AtoElement {
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
export class AtoBlock extends AtoElement {
    defaults() {
        return {
            ...super.defaults(),
            type: "AtoBlock",
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
                    text: "",
                    fill: "black",
                    textVerticalAnchor: "middle",
                    fontSize: settings_dict['block']['label']['fontSize'],
                    fontWeight: settings_dict["block"]['label']["fontWeight"],
                    textAnchor: "middle",
                    fontFamily: settings_dict["common"]["fontFamily"],
                    x: 'calc(w/2)',
                    y: 'calc(h/2)'
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

// Class for a interface
export class AtoInterface extends AtoElement {
    defaults() {
        return {
            ...super.defaults(),
            type: "AtoInterface",
            collapsed: false,
            attrs: {
                body: {
                    fill: "transparent",
                    stroke: 'green',
                    strokeWidth: 3,
                    width: "calc(w)",
                    height: "calc(h)",
                    rx: settings_dict["block"]["boxRadius"],
                    ry: settings_dict["block"]["boxRadius"],
                },
                label: {
                    text: "",
                    fill: "black",
                    textVerticalAnchor: "middle",
                    fontSize: settings_dict['block']['label']['fontSize'],
                    fontWeight: settings_dict["block"]['label']["fontWeight"],
                    textAnchor: "middle",
                    fontFamily: settings_dict["common"]["fontFamily"],
                    x: 'calc(w/2)',
                    y: 'calc(h/2)'
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
    AtoBlock,
    AtoInterface
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
            return [0, settings_dict['component']['portLabelToBorderGap']];
        case "bottom":
            return [0, - settings_dict['component']['portLabelToBorderGap']];
        case "left":
            return [settings_dict['component']['portLabelToBorderGap'], 0];
        case "right":
            return [- settings_dict['component']['portLabelToBorderGap'], 0];
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

function getPortPosition(location, pin_list, port_offset, max_length) {
    // Make sure that the port offset results in having ports on the grid
    var center_offset = normalizeDimensionToGrid((port_offset + max_length / 2), settings_dict['common']['gridSize']);
    var port_start_position = 0;
    if ((pin_list.length / 2) % 1 == .5) {
        port_start_position = pin_list.length / 2 * settings_dict['common']['gridSize'];
    }
    else {
        port_start_position = (pin_list.length / 2 + 0.5) * settings_dict['common']['gridSize'];
    }
    var port_length = pin_list.length * settings_dict['common']['gridSize'];
    switch (location) {
        case "top":
            return {
                name: 'line',
                args: {
                    start: { x: center_offset - port_start_position, y: 0 },
                    end: { x: center_offset - port_start_position + port_length, y: 0 }
                },
            };
        case "bottom":
            return {
                name: 'line',
                args: {
                    start: { x: center_offset - port_start_position, y: 'calc(h)' },
                    end: { x: center_offset - port_start_position + port_length, y: 'calc(h)' }
                },
            };
        case "left":
            return {
                name: 'line',
                args: {
                    start: { x: 0, y: center_offset - port_start_position },
                    end: { x: 0, y: center_offset - port_start_position + port_length }
                },
            };
        case "right":
            return {
                name: 'line',
                args: {
                    start: { x: 'calc(w)', y: center_offset - port_start_position },
                    end: { x: 'calc(w)', y: center_offset - port_start_position + port_length }
                },
            };
        default:
            return 0;
    };
};


function getElementTitle(name, instance_of) {
    if (instance_of != null) {
        return `${name} \n(${instance_of})`;
    } else {
        return name;
    }
}

// TODO: this function should be made recursive inside the main process block function
function processLocals(jointJSObject, locals, config) {

    for (let element of locals) {
        const allowedTypes = ['signal', 'pin', 'interface'];
        if (allowedTypes.includes(element['type'])) {
            let pin_to_add = {
                "path": element['name'],
                "name": element['name'],
            }
            let port_location = 'top';
            for (let config_pin of ((config || {}).pins || [])) {
                // If a port is defined, add it to it designated port
                if (pin_to_add['name'] == config_pin['name']) {
                    port_location = config_pin['port'];
                }
            }
            jointJSObject.addPortSingle(pin_to_add['path'], pin_to_add['name'], port_location);
        }
    }
}

export function createComponent(name, instance_of, locals, config) {
    let title = getElementTitle(name, instance_of);
    var component = new AtoComponent({
        id: name,
        instance_name: name,
        size: {
            width: 10,
            height: 10
        },
        attrs: {
            label: {
                text: title,
            }
        },
    });
    if (isIterable(locals)) {
        processLocals(component, locals, config);
    }
    //TODO: move this function to the constructor
    component.createDefaultPorts();
    component.resizeBasedOnContent();

    return component;
}

export function createBlock(name, instance_of, locals, config) {
    let title = getElementTitle(name, instance_of);
    let block = new AtoBlock({
        id: name,
        instance_name: name,
        size: {
            width: 200,
            height: 100
        },
        attrs: {
            label: {
                text: title,
            }
        },
    });
    if (isIterable(locals)) {
        processLocals(block, locals, config);
    }
    block.createDefaultPorts();

    return block;
}

export function createInterface(name, instance_of, locals) {
    let title = getElementTitle(name, instance_of);
    let intfc = new AtoInterface({
        id: name,
        instance_name: name,
        size: {
            width: 200,
            height: 100
        },
        attrs: {
            label: {
                text: title,
            }
        },
    });

    if (isIterable(locals)) {
        processLocals(intfc, locals);
    }

    return intfc;
}

export function createRoot(name, file_name) {
    let root = new AtoBlock({
        id: name,
        instance_name: name,
        file_name: file_name,
        size: {
            width: 200,
            height: 100
        },
    });

    return root;
}

function addElementToElement(block_to_add, to_block) {
    to_block.embed(block_to_add);
}

export async function processBlock(element, file_name, is_root, graph) {
    let joint_object = null;
    switch (element['type']) {
        case 'component':
            joint_object = createComponent(element['name'], element['instance_of'], element['locals'], element['config'][element['instance_of']]);
            joint_object.resizeBasedOnContent();
            joint_object.addTo(graph);
            //addElementToElement(joint_object, joint_root);
            break;
        // This is kind of dirty, might make sense to have Bob update this
        case 'module':
            if (is_root) {
                joint_object = createRoot(element['name'], file_name);
                joint_object.addTo(graph);
                processLocals(joint_object, element['locals']);
            }
            else {
                joint_object = createBlock(element['name'], element['instance_of'], element['locals'], element['config'][element['instance_of']]);
                joint_object.addTo(graph);
                //addElementToElement(joint_object, joint_root);
            }
            joint_object.resizeBasedOnContent();
            break;
        case 'interface':
            break;
        case 'link':
            joint_object = createLink(element['name'], element['source_connectable'], element['target_connectable'], element['source_connectable_type'], element['target_connectable_type'], element['source_block'], element['target_block'], element['above_source_block'], element['above_target_block'], element['source_block_type'], element['target_block_type'], element['above_source_block_type'], element['above_target_block_type'], graph);
            break;
        case 'signal':
            break;
        //TODO: the dict from Bob comes with a last empty element for an unkonwn reason
        default:
            console.log('Unknown element type: ' + element['type']);
    }

    // If element is the root, call the function recursively to build the elements within it
    if (is_root) {
        for (let sub_element of element['locals']) {
            let return_joint_element = await processBlock(sub_element, file_name, false, graph);
            if (return_joint_element instanceof AtoComponent || return_joint_element instanceof AtoBlock) {
                addElementToElement(return_joint_element, joint_object);
            }
        }
    }
    return joint_object;
}


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
            targetMarker: { 'type': 'none' },
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
            offset: -6,
            angle: 0,
            args: {
                keepGradient: true,
                ensureLegibility: true,
            }
        }
    });

    return added_stub;
}

//TODO: Add interface and add stubs look very similar. Can they be combined?
function addInterface(block_id, port_id, label) {
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
            'stroke': settings_dict['interface']['color'],
            'stroke-width': settings_dict['interface']['strokeWidth'],
            targetMarker: { 'type': 'none' },
        },
        z: 0,
    });
    added_stub.appendLabel({
        attrs: {
            text: {
                text: label,
                fontFamily: settings_dict['common']['fontFamily'],
                fontSize: settings_dict['interface']['fontSize'],
                //textVerticalAnchor: "middle",
                textAnchor: "middle",
            }
        },
        position: {
            distance: .9,
            offset: -7,
            angle: 0,
            args: {
                keepGradient: true,
                ensureLegibility: true,
            }
        }
    });

    return added_stub;
}

function addLink(source_block_id, source_port_id, target_block_id, target_port_id, stroke_width) {
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
            'stroke-width': stroke_width,
            targetMarker: { 'type': 'none' },
        },
        z: 0
    });
    added_link.router('manhattan', {
        perpendicular: true,
        step: settings_dict['common']['gridSize'] / 2,
    });

    return added_link;
}

//TODO: this is a ratsnest. We need to update the logic here.
export function createLink(name, source_con, target_con, source_con_type, target_con_type, source_block, target_block, above_source_block, above_target_block, source_block_type, target_block_type, above_source_block_type, above_target_block_type, graph) {
    let added_link;
    let allowedInterface = ['interface'];
    let allowedBlock = ['component', 'module'];
    if ((allowedInterface.includes(source_block_type) && allowedInterface.includes(target_block_type)) && above_source_block_type != 'self' && above_target_block_type != 'self') {
        added_link = addLink(above_source_block, source_block, above_target_block, target_block, settings_dict['interface']['strokeWidth']);
        added_link.addTo(graph);
    }
    else if (allowedBlock.includes(source_block_type) && allowedBlock.includes(target_block_type)) {
        added_link = addLink(source_block, source_con, target_block, target_con, settings_dict['link']['strokeWidth']);
        added_link.addTo(graph);
    }
    else {
        if (((source_block_type == "self" || source_block_type == "module" || source_block_type == "component") && target_block_type == "interface") || ((target_block_type == "self" || target_block_type == "module" || target_block_type == "component") && source_block_type == "interface")) {
            if (source_block_type == "interface") {
                added_link = addInterface(target_block, target_con, source_block + '.' + source_con);
                added_link.addTo(graph);
            }
            if (target_block_type == "interface") {
                added_link = addInterface(source_block, source_con, target_block + '.' + target_con);
                added_link.addTo(graph);
            }
        }
        if ((source_block_type == "interface" && target_block_type == "interface")) {
            added_link = addInterface(above_source_block, source_block, target_block);
            added_link.addTo(graph);
            added_link = addInterface(above_target_block, target_block, source_block);
            added_link.addTo(graph);
        }
        if ((source_block_type == "self" && above_source_block_type == "self") && ((target_block_type == "module" || target_block_type == "component") && above_target_block_type == "self")) {
            added_link = addStub(target_block, target_con, name);
            added_link.addTo(graph);
        }
        if (((source_block_type == "module" || source_block_type == "component") && above_source_block_type == "self") && (target_block_type == "self" && above_target_block_type == "self")) {
            added_link = addStub(source_block, source_con, name);
            added_link.addTo(graph);
        }
    }

    return added_link;
}

export function customAnchor(view, magnet, ref, opt, endType, linkView) {
    const elBBox = view.model.getBBox();
    const magnetCenter = view.getNodeBBox(magnet).center();
    const side = elBBox.sideNearestToPoint(magnetCenter);
    let dx = 0;
    let dy = 0;
    const length = ('length' in opt) ? opt.length : 35;
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
    return anchors.center.call(this, view, magnet, ref, {
        ...opt,
        dx,
        dy
    }, endType, linkView);
}