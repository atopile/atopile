// TODO: the root cell ID has a colon in it, which there shouldn't be

//import { settings_dict } from "./vis_settings";

import { shapes, util, dia, anchors } from 'jointjs';
import { returnConfigFileName,
    concatenateParentPathAndModuleName,
    computeNameDepth,
    provideFirstNameElementFromName,
    provideLastPathElementFromPath } from './path';

import { AtoElement, AtoBlock, AtoComponent, createBlock, createComponent, addLinks, customAnchor } from "./joint_element";

import { settings_dict } from './viewer_settings';


const cellNamespace = {
    ...shapes,
    AtoElement,
    AtoComponent,
    AtoBlock
};


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
                    let added_element = addLinks(element, downstream_path, joint_object.getEmbeddedCells());
                    for (let element of added_element) {
                        element.addTo(graph);
                    }
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
                joint_object.resizeBasedOnContent();
                applyParentConfig(element, child_attrs);
                console.log('Bt port contains:')
                console.log(joint_object);
                console.log(joint_object.getGroupPorts('bottom'));

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
    drawGrid: { name: 'dot', args: { color: 'black' }},
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
