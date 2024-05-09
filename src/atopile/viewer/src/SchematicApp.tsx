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
    useStore,
    useKeyPress,
    useUpdateNodeInternals,
    applyNodeChanges
} from 'reactflow';
import 'reactflow/dist/style.css';

import SimpleTable from './LinkTable.tsx';

import './index.css';

import "react-data-grid/lib/styles.css";
import { Resistor } from './components/SchematicElements.tsx';
import { ZenerDiode } from './components/diodes.tsx';


const nodeTypes = {
    Resistor: Resistor,
    ZenerDiode: ZenerDiode
};

const edgeTypes = {};

async function loadSchematicJsonAsDict() {
    const response = await fetch('http://127.0.0.1:8080/schematic');
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
}

let request_ratsnest_update = false;
let nets = [];
let nets_distance = [];
let port_to_component_map = {};


const AtopileSchematicApp = ({ viewBlockId }) => {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const { fitView } = useReactFlow();
    const [isDataLoaded, setIsDataLoaded] = useState(false);

    const rotateAction = useKeyPress(['r', 'R']);
    const mirrorAction = useKeyPress(['f', 'F']);
    const updateNodeInternals = useUpdateNodeInternals();

    useEffect(() => {
        const updateNodesFromJson = async () => {
            try {
                const fetchedNodes = await loadSchematicJsonAsDict();
                //handleBlockLoad("root");

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
                        populatedNodes.push({ id: component_name, type: component_data["instance_of"], data: component_data, position: position });
                    } else if (component_data['std_lib_id'] == 'Capacitor') {
                        populatedNodes.push({ id: component_name, type: 'Capacitor', data: component_data, position: position });
                    } else if (component_data['std_lib_id'] == 'OpAmp') {
                        populatedNodes.push({ id: component_name, type: 'OpAmp', data: component_data , position: position });
                    } else if (component_data['std_lib_id'] == 'NPN') {
                        populatedNodes.push({ id: component_name, type: 'NPN', data: component_data , position: position });
                    } else if (component_data['std_lib_id'] == 'LED') {
                        populatedNodes.push({ id: component_name, type: "LED", data: {component_data: component_data, orientation: orientation}, position: position });
                    } else if (component_data['std_lib_id'] == 'Diode') {
                        populatedNodes.push({ id: component_name, type: "Diode", data: {component_data: component_data, orientation: orientation}, position: position });
                    } else if (component_data['std_lib_id'] == 'ZenerDiode') {
                        populatedNodes.push({ id: component_name, type: "ZenerDiode", data: component_data, position: position });
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
        setIsDataLoaded(true);
    }, [viewBlockId]);

    useEffect(() => {
        let updatedNodes = [];
        updatedNodes = nodes.map((node) => {
            if (node.selected) {
                return {
                    ...node,
                    data: {
                        ...node.data,
                        rotation: rotateAction? (node.data.rotation + 90) % 360 : node.data.rotation,
                        mirror: mirrorAction? !node.data.mirror : node.data.mirror,
                    }
                };
                // node.data = {
                //     ...node.data,
                //     rotation: rotateAction? (node.data.rotation + 90) % 360 : node.data.rotation,
                //     mirror: mirrorAction? !node.data.mirror : node.data.mirror,
                // };
            }
            //updateNodeInternals(node.id);
            return node;
        });
        setNodes(updatedNodes);
        // if (shouldUpdateInternals) {
            // Delay the internals update to ensure it happens after the state update
        //setTimeout(() => updateNodeInternals(("/Users/timot/Dev/atopile/community-projects/demo-p…oProject::esd_protection_fet_src_gate_zener_diode"), 10));
        // for (const node of updatedNodes) {
        //     console.log(node);
        //     updateNodeInternals(node.id);
        // }
    }, [rotateAction, mirrorAction]);

    // const onNodeChange = useCallback(
    //     (changes) => {
    //       setNodes((oldNodes) => applyNodeChanges(changes, oldNodes));
    //     },
    //     [setNodes],
    //   );
    function handleUpdateNodes() {
        console.log("Updating node");
        updateNodeInternals("/Users/timot/Dev/atopile/community-projects/demo-p…oProject::esd_protection_fet_src_gate_zener_diode");
    }

    useEffect(() => {
        setTimeout(() => {
          const node = nodeInternals.get(props.id);
          const propSymbols = Object.getOwnPropertySymbols(node);
          const handleBounds = node[propSymbols[0]].handleBounds;
          const orphans = edges.filter(
            (e) =>
              e.source === node.id &&
              !handleBounds.source.find((h) => h.id === e.sourceHandle)
          );
          reactFlowInstance.deleteElements({ edges: orphans });
        }, 0);
      }, [nodeInternals, props.id, edges, reactFlowInstance]);

    const onSelectionChange = (elements) => {
        if (request_ratsnest_update && isDataLoaded) {
            request_ratsnest_update = false;
            addLinks();
            return;
        }
        request_ratsnest_update = true;
    };

    function addLinks() {
        try {
            // Add the shortest links to complete all the nets
            // Get all the component positions
            let component_positions = {};
            for (const node of nodes) {
                component_positions[node.id] = node.position;
            }
            // for each component in the net, calculate the distance to the other components in the net
            let nets_distances = [];
            let test = nets;
            for (const net of test) {
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
        } catch (error) {
            console.error("Failed to add links:", error);
        }
    }

    return (
    <div className="providerflow">
        <ReactFlowProvider>
        <ReactFlow
            key={"schematic"}
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onSelectionChange={onSelectionChange}
            fitView
            edgeTypes={edgeTypes}
            nodeTypes={nodeTypes}
            style={{ width: '100%', height: '50%' }}
        >
        {/* <Panel position="top-left">
            <div style={{backgroundColor: 'lightgray', border: '2px solid grey', margin: '10px', padding: '10px', borderRadius: '10px'}}>
                <div style={{textAlign: 'center'}}> Model inspection pane</div>
                <div><i>Inspecting:</i> <b>{block_id}</b></div>
                <div><i>Parent:</i> {parent_block_addr}</div>
            </div>
        </Panel> */}
        <Background />
        </ReactFlow>
        </ReactFlowProvider>
        <button onClick={() => {
            handleUpdateNodes();
        }}>
            Update nodes
        </button>
    </div>
    );
};

export default AtopileSchematicApp;
