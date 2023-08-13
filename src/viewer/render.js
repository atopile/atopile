// TODO: the root cell ID has a colon in it, which there shouldn't be

//import { settings_dict } from "./vis_settings";

import { shapes, util, dia, anchors } from 'jointjs';
import { returnConfigFileName,
    concatenateParentPathAndModuleName,
    computeNameDepth,
    provideFirstNameElementFromName,
    provideLastPathElementFromPath } from './path';

import { AtoElement, AtoBlock, AtoComponent, createBlock, createComponent } from "./joint_element";

import { settings_dict } from './viewer_settings';


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
    return anchors.center.call(this, view, magnet, ref, {
      ...opt,
      dx,
      dy
    }, endType, linkView);
}



const cellNamespace = {
    ...shapes,
    AtoElement,
    AtoComponent,
    AtoBlock
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

// Return the cell id and port id from port name and current path
// If the link spans deeper than one module, a port is added to the module
// TODO: what happens if the port is multiple layers deep?
// TODO: Currently only adding the top link
function getLinkAddress(port, current_path, embedded_cells) {
    let port_path = concatenateParentPathAndModuleName(current_path, port);
    let port_name_depth = computeNameDepth(port);
    let cell_id;
    let first_element;

    switch (port_name_depth) {
        case 1:
            cell_id = current_path;
            break;
        case 2:
            first_element = provideFirstNameElementFromName(port);
            cell_id = concatenateParentPathAndModuleName(current_path, first_element['first_name']);
            break;
        default:
            console.log('default');
            first_element = provideFirstNameElementFromName(port);
            cell_id = concatenateParentPathAndModuleName(current_path, first_element['first_name']);
            for (let cell of embedded_cells) {
                if (cell['id'] == cell_id) {
                    cell.addPortWithPins('top', 'top', [{'path': port_path, 'name': first_element['remaining']}])
                }
            }
            break;
    }
    console.log({'cell_id': cell_id, 'port_id': port_path});
    return {'cell_id': cell_id, 'port_id': port_path};
}


function addLinks(element, current_path, embedded_cells) {
    for (let link of element['links']) {
        let source_address = getLinkAddress(link['source'], current_path, embedded_cells);
        let target_address = getLinkAddress(link['target'], current_path, embedded_cells);

        let is_stub = false;
        for (let link_config of ((element.config || {}).signals || [])) {
            if (link_config['name'] == link['name'] && link_config['is_stub']) {
                is_stub = true;
                // if not a module (don't want stubs at module level)
                if (current_path.length != source_address['cell_id'].length) {
                    addStub(source_address['cell_id'], source_address['port_id'], link['name']);
                }
                // if not a module (don;t want stubs at module level)
                if (current_path.length != target_address['cell_id'].length) {
                    addStub(target_address['cell_id'], target_address['port_id'], link['name']);
                }
            }
        }
        if (!is_stub) {
            addLink(source_address['cell_id'], source_address['port_id'], target_address['cell_id'], target_address['port_id']);
        }
    }
}


function addElementToElement(block_to_add, to_block) {
    to_block.embed(block_to_add);
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
                downstream_path = concatenateParentPathAndModuleName(path, element['name']);
                joint_object = createComponent(element, parent, downstream_path);
                joint_object.addTo(graph);
                element['jointObject'] = joint_object;
                if (parent) {
                    addElementToElement(joint_object, parent);
                }
                applyParentConfig(element, child_attrs);
            }

            // If it is a block, create it and instantiate the contents within it
            else if (element['type'] == 'module') {
                downstream_path = concatenateParentPathAndModuleName(path, element['name']);
                // Create the module
                joint_object = createBlock(element, parent, downstream_path);
                joint_object.addTo(graph);
                element['jointObject'] = joint_object;
                if (parent) {
                    addElementToElement(joint_object, parent);
                }

                // Call the function recursively on children
                if (await generateJointjsGraph(element['blocks'], max_depth, new_depth, downstream_path, joint_object, element['config']['child_attrs'])) {
                    addLinks(element, downstream_path, joint_object.getEmbeddedCells());
                    // change the title layout to the corner for module with embedded childrens
                    joint_object.attr({
                        label: {
                            textVerticalAnchor: "top",
                            textAnchor: "start",
                            x: 8,
                            y: 8
                        }
                    });
                }
                applyParentConfig(element, child_attrs);

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
                downstream_path = concatenateParentPathAndModuleName(path, element['name']);
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
    let config_location_name;

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
const paper = new dia.Paper({
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
        ...anchors,
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
