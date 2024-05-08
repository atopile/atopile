// @ts-nocheck
import React, { useCallback, useEffect, useLayoutEffect, useState } from 'react';
import ReactFlow, {
    addEdge,
    Background,
    useNodesState,
    useEdgesState,
    MarkerType,
    useReactFlow,
    ReactFlowProvider,
    Panel,
    Position,
    isEdge,
    Edge,
    useStore
} from 'reactflow';
import 'reactflow/dist/style.css';

import { createNodesAndEdges } from './utils.tsx';
import { CustomNodeBlock, CircularNodeComponent } from './CustomNode.tsx';
import CustomEdge from './CustomEdge.tsx';

import SimpleTable from './LinkTable.tsx';

import './index.css';

import ELK from 'elkjs/lib/elk.bundled.js';


import "react-data-grid/lib/styles.css";
import { Resistor,
    Capacitor,
    Ground,
    Vcc,
    Signal,
    Bug,
    OpAmp,
    LED,
    NPN,
    PNP,
    NFET,
    PFET,
    Diode,
    ZenerDiode,
    SchottkyDiode,
    loadSchematicJsonAsDict } from './SchematicElements.tsx';

const { nodes: initialNodes, edges: initialEdges } = createNodesAndEdges();


const nodeTypes = {
    Resistor: Resistor,
    Capacitor: Capacitor,
    LED: LED,
    GroundNode: Ground,
    VccNode: Vcc,
    Signal: Signal,
    BugNode: Bug,
    OpAmp: OpAmp,
    NPN: NPN,
    NFET: NFET,
    PFET: PFET,
    Diode: Diode,
    ZenerDiode: ZenerDiode,
    SchottkyDiode: SchottkyDiode,
};

const edgeTypes = {
    custom: CustomEdge,
};

async function loadJsonAsDict() {
    const response = await fetch('http://127.0.0.1:8080/block-diagram');
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
}

const block_id = "root";
const parent_block_addr = "none";
let request_ratsnest_update = false;
let nets = [];
let nets_distance = [];
let port_to_component_map = {};


const AtopileViewer = () => {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const { fitView } = useReactFlow();
    const [block_id, setBlockId] = useState("root");
    const [parent_block_addr, setParentBlockAddr] = useState("none");

    useEffect(() => {
        const updateNodesFromJson = async () => {
            try {
                const fetchedNodes = await loadSchematicJsonAsDict();

                const populatedNodes = [];
                for (const [component_name, component_data] of Object.entries(fetchedNodes['components'])) {
                    const position = {
                        x: Math.random() * window.innerWidth,
                        y: Math.random() * window.innerHeight,
                    };
                    let orientation = "horizontal";
                    if (component_data['contacting_power']) {
                        orientation = "vertical";
                    }
                    if (component_data['std_lib_id'] == 'Resistor') {
                        populatedNodes.push({ id: component_name, type: component_data["instance_of"], data: {component_data: component_data, orientation: orientation}, position: position });
                    } else if (component_data['std_lib_id'] == 'Capacitor') {
                        populatedNodes.push({ id: component_name, type: 'Capacitor', data: {component_data: component_data, orientation: orientation} , position: position });
                    } else if (component_data['std_lib_id'] == 'OpAmp') {
                        populatedNodes.push({ id: component_name, type: 'OpAmp', data: component_data , position: position });
                    } else if (component_data['std_lib_id'] == 'NPN') {
                        populatedNodes.push({ id: component_name, type: 'NPN', data: component_data , position: position });
                    } else if (component_data['std_lib_id'] == 'LED') {
                        populatedNodes.push({ id: component_name, type: "LED", data: {component_data: component_data, orientation: orientation}, position: position });
                    } else if (component_data['std_lib_id'] == 'Diode') {
                        populatedNodes.push({ id: component_name, type: "Diode", data: {component_data: component_data, orientation: orientation}, position: position });
                    } else if (component_data['std_lib_id'] == 'ZenerDiode') {
                        populatedNodes.push({ id: component_name, type: "ZenerDiode", data: {component_data: component_data, orientation: orientation}, position: position });
                    } else if (component_data['std_lib_id'] == 'SchottkyDiode') {
                        populatedNodes.push({ id: component_name, type: "SchottkyDiode", data: {component_data: component_data, orientation: orientation}, position: position });
                    } else if (component_data['std_lib_id'] == 'NFET') {
                        populatedNodes.push({ id: component_name, type: "NFET", data: {component_data: component_data, orientation: orientation}, position: position });
                    } else if (component_data['std_lib_id'] == 'PFET') {
                        populatedNodes.push({ id: component_name, type: "PFET", data: {component_data: component_data, orientation: orientation}, position: position });
                    } else {
                        // populatedNodes.push({ id: component_name, type: 'BugNode', data: component_data , position: position });
                    }
                    for (const port in component_data['ports']) {
                        port_to_component_map[component_data['ports'][port]['net_id']] = component_name;
                    }
                }
                for (const [signal_name, signal_data] of Object.entries(fetchedNodes['signals'])) {
                    const position = {
                        x: Math.random() * window.innerWidth,
                        y: Math.random() * window.innerHeight,
                    };
                    if (signal_data['std_lib_id'] == 'Power.vcc') {
                        populatedNodes.push({ id: signal_name, type: 'VccNode', data: signal_data , position: position });
                    } else if (signal_data['std_lib_id'] == 'Power.gnd') {
                        populatedNodes.push({ id: signal_name, type: 'GroundNode', data: signal_data , position: position });
                    } else {
                        //populatedNodes.push({ id: signal_name, type: 'Signal', data: signal_data , position: position });
                    }
                    port_to_component_map[signal_name] = signal_name;
                }
                // Assuming fetchedNodes is an array of nodes in the format expected by React Flow
                setNodes(populatedNodes);

                nets = fetchedNodes['nets'];

            } catch (error) {
                console.error("Failed to fetch nodes:", error);
            }
        };

        updateNodesFromJson();
    }, [block_id]);

    const onSelectionChange = (elements) => {
        if (request_ratsnest_update) {
            request_ratsnest_update = false;
            addLinks();
            return;
        }
        request_ratsnest_update = true;
    };

    function addLinks() {
        // Get all the component positions
        let component_positions = {};
        for (const node of nodes) {
            component_positions[node.id] = node.position;
        }
        // for each component in the net, calculate the distance to the other components in the net
        let nets_distances = [];
        for (const net of nets) {
            let net_distances = {};
            for (const conn_id of net) {
                let conn_to_conn_distance = {};
                for (const other_conn_id of net) {
                    if (conn_id != other_conn_id) {
                        const conn_pos = component_positions[port_to_component_map[conn_id]];
                        const other_conn_pos = component_positions[port_to_component_map[other_conn_id]];
                        conn_to_conn_distance[other_conn_id] = Math.sqrt(Math.pow(conn_pos.x - other_conn_pos.x, 2) + Math.pow(conn_pos.y - other_conn_pos.y, 2));
                    }
                }
                net_distances[conn_id] = conn_to_conn_distance;
            }
            nets_distances.push(net_distances);
        }

        // nearest neighbor algorithm https://en.wikipedia.org/wiki/Nearest_neighbour_algorithm
        let conn_visited = {};
        for (const net of nets) {
            for (const conn_id of net) {
                conn_visited[conn_id] = false;
            }
        }

        let links_to_add = {};
        for (const net of nets_distances) {
            for (const conn_id in net) {
                if (conn_visited[conn_id]) {
                    continue;
                }
                let closest_conn_id = "none";
                let closest_conn_distance = Infinity;
                for (const other_conn_id in net) {
                    if (conn_id == other_conn_id) {
                        continue;
                    }
                    if (net[conn_id][other_conn_id] < closest_conn_distance && conn_visited[other_conn_id] === false) {
                        closest_conn_id = other_conn_id;
                        closest_conn_distance = net[conn_id][other_conn_id];
                    }
                }
                conn_visited[conn_id] = true;
                links_to_add[conn_id] = closest_conn_id;
            }
        }

        const populatedEdges = [];
        for (const edge in links_to_add) {
            populatedEdges.push({
                id: edge + links_to_add[edge],
                source: port_to_component_map[edge],
                sourceHandle: edge,
                target: port_to_component_map[links_to_add[edge]],
                targetHandle: links_to_add[edge],
                type: 'step',
                style: {
                    stroke: 'black',
                    strokeWidth: 2,
                },
            });
        }
        setEdges(populatedEdges);
    }

    return (
    <div className="floatingedges">
        <ReactFlow
            key={block_id}
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onSelectionChange={onSelectionChange}
            //onConnect={onConnect}
            fitView
            edgeTypes={edgeTypes}
            nodeTypes={nodeTypes}
            style={{ width: '100%', height: '50%' }}
        >
        <Panel position="top-left">
            <div style={{backgroundColor: 'lightgray', border: '2px solid grey', margin: '10px', padding: '10px', borderRadius: '10px'}}>
                <div style={{textAlign: 'center'}}> Model inspection pane</div>
                <div><i>Inspecting:</i> <b>{block_id}</b></div>
                <div><i>Parent:</i> {parent_block_addr}</div>
                <button onClick={() => handleExpandClick(parent_block_addr)}>return</button>
                <button onClick={() => onLayout({ direction: 'DOWN' })}>re-layout</button>
            </div>
        </Panel>
        <Background />
        </ReactFlow>
    </div>
    );
};


function App() {
    return (
        <ReactFlowProvider>
            <AtopileViewer />
        </ReactFlowProvider>
    );
}

export default App;