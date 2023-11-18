import { shapes, dia, anchors } from 'jointjs';
import { returnConfigFileName} from './path';

import { AtoElement, AtoBlock, AtoComponent, AtoInterface, processBlock, customAnchor } from "./ato_element";

import { settings_dict } from './viewer_settings';


const cellNamespace = {
    ...shapes,
    AtoElement,
    AtoComponent,
    AtoBlock
};


async function generateJointjsRoot(circuit, file_name) {
    let joint_object = await processBlock(circuit, file_name, true, graph);

    // Apply the positions to cells
    let embedded_cells = joint_object.getEmbeddedCells();
    if (circuit['name'] in circuit['config']) {
        let object_config = circuit['config'][circuit['name']];
        for (let cell of embedded_cells) {
            for (let conf_cell in object_config['child_attrs']) {
                if (cell.id == conf_cell) {
                    cell.applyParentAttrs(object_config['child_attrs'][conf_cell])
                }
            }
        }
    }
    return joint_object;
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

paper.on('link:mouseenter', function(linkView) {
    linkView.showTools();
    linkView.highlight();
});

paper.on('link:mouseleave', function(linkView) {
    linkView.hideTools();
    linkView.unhighlight();
});

graph.on('change:position', function(cell) {
    cell.fitAncestorElements();
});

function getConfigFilenameFromAto(ato_file_name) {
    // Strip .ato from the name
    let striped_file_name = ato_file_name.replace(".ato", "");
    return  striped_file_name + '.vis.json';
}

// Fetch a circuit dict from the server
async function loadCircuit() {
    const urlParams = new URLSearchParams(window.location.search);
    const response = await fetch('/api/circuit/' + urlParams.get('circuit'));
    const file_name = returnConfigFileName(urlParams.get('circuit'));

    const circuit_data = await response.json();
    console.log("data received from backend")
    console.log(circuit_data);

    let jointJSRoot = await generateJointjsRoot(circuit_data, file_name.file);
}

// flag to help rate limit calls to savePositions
var stuff_has_moved = false;

paper.on('cell:pointerup', function(cell, evt, x, y) {
    if (cell.model instanceof AtoComponent || cell.model instanceof AtoBlock || cell.model instanceof AtoInterface) {
        stuff_has_moved = true;
    }
});

function savePositions() {
    let requests_to_make = {};

    graph.getCells().forEach(function(cell) {
        if (cell instanceof AtoComponent || cell instanceof AtoBlock || cell instanceof AtoInterface) {
            console.log(cell.id);

            let parent = cell.getParentCell();
            if (!parent) return; // skip the root element

            let origin_file = getConfigFilenameFromAto(parent.attributes.file_name);
            let origin_module = parent.id;
            let instance_name = cell.id;

            if (!requests_to_make[origin_file]) requests_to_make[origin_file] = {};
            if (!requests_to_make[origin_file][origin_module]) requests_to_make[origin_file][origin_module] = {"child_attrs": {}};
            requests_to_make[origin_file][origin_module]["child_attrs"][instance_name] = {
                "position": {
                    x: cell.attributes.position.x,
                    y: cell.attributes.position.y
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
