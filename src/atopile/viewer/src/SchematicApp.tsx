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
    applyNodeChanges,
    BackgroundVariant
} from 'reactflow';
import 'reactflow/dist/style.css';


import SimpleTable from './LinkTable.tsx';

import './index.css';

import "react-data-grid/lib/styles.css";
import { SchematicComponent, SchematicSignal, SchematicScatter } from './components/SchematicElements.tsx';

import { useURLBlockID } from './utils.tsx';

const nodeTypes = {
    SchematicComponent: SchematicComponent,
    SchematicSignal: SchematicSignal,
    SchematicScatter: SchematicScatter
};

const edgeTypes = {};

async function loadSchematicJsonAsDict() {
    const response = await fetch('http://127.0.0.1:8080/schematic-data');
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
}

let request_ratsnest_update = false;
let nets = [];
let nets_distance = [];
let port_to_component_map = {};
let component_positions = {};


const AtopileSchematic = ({ viewBlockId, savePos, handleLoad }) => {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const { fitView } = useReactFlow();
    const [loading, setLoading] = useState(true);
    const [tooLarge, setTooLarge] = useState(false);

    const rotateAction = useKeyPress(['r', 'R']);
    const mirrorAction = useKeyPress(['f', 'F']);

    // Save position once the user has finished dragging the node around
    const onNodeDragStop = (event, node, nodes) => {
        for (const node of nodes) {
            savePos(node.id, node.position, node.data.rotation, false, node.data.mirror);
        }
    };

    // Update the graph using data coming from the backend
    useEffect(() => {
        const updateNodesFromJson = async () => {
            try {
                const fetchedNodes = await loadSchematicJsonAsDict();
                const displayedNode = fetchedNodes[viewBlockId];

                if (Object.keys(displayedNode['components']).length > 1000) {
                    setTooLarge(true);
                    return;
                }

                const populatedNodes = [];
                for (const [component_name, component_data] of Object.entries(displayedNode['components'])) {
                    if (component_data['std_lib_id'] !== "") {
                        populatedNodes.push({ id: component_name, type: "SchematicComponent", data: component_data, position: component_data['position'] });
                        for (const port in component_data['ports']) {
                            port_to_component_map[component_data['ports'][port]['net_id']] = component_name;
                        }
                    } else {
                        Object.entries(component_data['ports']).forEach(([port_id, port_data], index) => {
                            populatedNodes.push({
                                id: port_data['net_id'],
                                type: "SchematicScatter",
                                data: { id: port_data['net_id'], name: port_data['name'], rotation: 0, mirror: port_data['mirror_y'] },
                                position: port_data['position']
                            });
                            port_to_component_map[port_data['net_id']] = port_data['net_id'];
                        });
                    }
                }
                // for (const [signal_name, signal_data] of Object.entries(displayedNode['signals'])) {
                //     const position = {
                //         x: Math.random() * window.innerWidth,
                //         y: Math.random() * window.innerHeight,
                //     };
                //     if (signal_data['std_lib_id'] !== "") {
                //         populatedNodes.push({ id: signal_name, type: "SchematicSignal", data: signal_data, position: position });
                //         port_to_component_map[signal_name] = signal_name;
                //     }
                // }
                // Assuming displayedNode is an array of nodes in the format expected by React Flow
                setNodes(populatedNodes);

                nets = displayedNode['nets'];

            } catch (error) {
                console.error("Failed to fetch nodes:", error);
            }
        };

        updateNodesFromJson();
        handleLoad('schematic');
        setLoading(false);
    }, [viewBlockId]);

    // Rerender nodes if rotation or mirroring is requested + save their state
    useEffect(() => {
        let updatedNodes = [];
        updatedNodes = nodes.map((node) => {
            if (node.selected) {
                //FIXME: this saves the mirror and rotationg state of nodes that don't have it enabled
                let rotation = rotateAction? (node.data.rotation + 90) % 360 : node.data.rotation;
                let mirror = mirrorAction? !node.data.mirror : node.data.mirror;

                // Only certain type of data is saved for certain types of nodes
                if (node.type === "SchematicScatter") {
                    savePos(node.id, node.position, 0, false, mirror);
                } else {
                    savePos(node.id, node.position, rotation, false, false);
                }
                return {
                    ...node,
                    data: {
                        ...node.data,
                        rotation: rotation,
                        mirror: mirror,
                    }
                };
            }
            return node;
        });
        setNodes(updatedNodes);
    }, [rotateAction, mirrorAction]);


    // Update links live when components are moved
    //FIXME: routing algorithms doesn't always seem to select shortest path
    const onSelectionChange = (elements) => {
        if (request_ratsnest_update && !loading) {
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
            //TODO: component position are now saved so this could be improved
            component_positions = {};
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
                        if (conn_id != other_conn_id && conn_id in port_to_component_map && other_conn_id in port_to_component_map) {
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
        {tooLarge ? (
        <div style={{ width: '100%', height: '50%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <b>There are more than 1000 components to display. Navigate to a different module.</b>
        </div>
      ) : (
        <ReactFlow
            key={"schematic"}
            snapToGrid={true}
            snapGrid={[15, 15]}
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onSelectionChange={onSelectionChange}
            onNodeDragStop={onNodeDragStop}
            fitView
            edgeTypes={edgeTypes}
            nodeTypes={nodeTypes}
            style={{ width: '100%', height: '50%' }}
        >
            <Background gap={15} variant={BackgroundVariant.Dots} />
        </ReactFlow>)}
    </div>
    );
};


export const AtopileSchematicApp = ({ savePos, handleLoad }) => {
    const { block_id } = useURLBlockID();
    return (
        <ReactFlowProvider>
            <AtopileSchematic
                viewBlockId={block_id}
                savePos={savePos}
                handleLoad={handleLoad}
            />
        </ReactFlowProvider>
    );
};

export default AtopileSchematicApp;
