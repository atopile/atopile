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
    Edge
} from 'reactflow';
import 'reactflow/dist/style.css';

import { CustomNodeBlock, ModuleNode, CircularNodeComponent } from './CustomNode.tsx';
import CustomEdge from './CustomEdge.tsx';

import SimpleTable from './LinkTable.tsx';

import './index.css';

import ELK from 'elkjs/lib/elk.bundled.js';

import "react-data-grid/lib/styles.css";

import { useURLBlockID } from './utils.tsx';


const elk = new ELK();

// Elk has a *huge* amount of options to configure. To see everything you can
// tweak check out:
//
// - https://www.eclipse.org/elk/reference/algorithms.html
// - https://www.eclipse.org/elk/reference/options.html
const elkOptions = {
    'elk.algorithm': 'layered',
    'elk.layered.spacing.nodeNodeBetweenLayers': '100',
    'elk.spacing.nodeNode': '80',
};

const getLayoutedElements = (nodes, edges, options = {}) => {
    const isHorizontal = options?.['elk.direction'] === 'RIGHT';
    const graph = {
        id: 'root',
        layoutOptions: options,
        children: nodes.map((node) => ({
            ...node,
            // Adjust the target and source handle positions based on the layout
            // direction.
            targetPosition: isHorizontal ? 'left' : 'top',
            sourcePosition: isHorizontal ? 'right' : 'bottom',

            // Hardcode a width and height for elk to use when layouting.
            width: 200,
            height: 50,
        })),
        edges: edges,
};

  return elk
    .layout(graph)
    .then((layoutedGraph) => ({
        nodes: layoutedGraph.children.map((node) => ({
            ...node,
            // React Flow expects a position property on the node instead of `x`
            // and `y` fields.
            position: { x: node.x, y: node.y },
        })),

        edges: layoutedGraph.edges,
    }))
    .catch(console.error);
};

const nodeTypes = {
    customNode: CustomNodeBlock,
    moduleNode: ModuleNode,
    customCircularNode: CircularNodeComponent
};

const edgeTypes = {
    custom: CustomEdge,
};

async function loadJsonAsDict() {
    const response = await fetch('http://127.0.0.1:8080/block-diagram-data');
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
}

const selected_link_data = [];
const selected_link_source = "none";
const selected_link_target = "none";
const requestRelayout = false;
let selected_links_data = {};


const AtopileBlockDiagram = ({ viewBlockId, savePos, handleLoad, reLayout, reLayoutCleared }) => {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const { fitView } = useReactFlow();
    const [selected_link_id, setSelectedLinkId] = useState("none");
    const [selected_link_data, setSelectedLinkData] = useState([]);
    const [selected_link_source, setSelectedLinkSource] = useState("none");
    const [selected_link_target, setSelectedLinkTarget] = useState("none");

    const handleLinkSelectClick = (newSelectedLinkId) => {
        setSelectedLinkId(newSelectedLinkId);
        setSelectedLinkData(selected_links_data[newSelectedLinkId]['links']);
        setSelectedLinkSource(selected_links_data[newSelectedLinkId]['source']);
        setSelectedLinkTarget(selected_links_data[newSelectedLinkId]['target']);
    };

    useEffect(() => {
        onLayout({ direction: "DOWN" });
        reLayoutCleared();
    }, [reLayout])

    const onLayout = useCallback(
    ({ direction }) => {
        const opts = { 'elk.direction': direction, ...elkOptions };
        getLayoutedElements(nodes, edges, opts).then(({ nodes: layoutedNodes, edges: layoutedEdges }) => {
            setNodes(layoutedNodes);
            setEdges(layoutedEdges);

            window.requestAnimationFrame(() => fitView());
        });
    }, [edges] );

    useEffect(() => {
        const updateNodesFromJson = async () => {
            try {
                const fetchedNodes = await loadJsonAsDict();
                const displayedNode = fetchedNodes[viewBlockId];
                handleLoad('block-diagram', displayedNode['parent']);
                const populatedNodes = [];
                for (const node in displayedNode['blocks']) {
                    const position = {
                    x: Math.random() * window.innerWidth,
                    y: Math.random() * window.innerHeight,
                    };
                    let style;
                    if (displayedNode['blocks'][node]['type'] == 'signal') {
                        populatedNodes.push({ id: node, type: 'customCircularNode', data: { title: node, instance_of: displayedNode['blocks'][node]['instance_of'], color: '#8ECAE6' }, position: position });
                    } else if (displayedNode['blocks'][node]['type'] == 'interface') {
                        populatedNodes.push({ id: node, type: 'customCircularNode', data: { title: node, instance_of: displayedNode['blocks'][node]['instance_of'], color: '#219EBC' }, position: position });
                    }
                    else if (displayedNode['blocks'][node]['type'] == 'module') {
                        populatedNodes.push({ id: node, type: 'moduleNode', data: { title: node, instance_of: displayedNode['blocks'][node]['instance_of'], address: displayedNode['blocks'][node]['address'], type: displayedNode['blocks'][node]['type'], color: '#FB8500' }, sourcePosition: Position.Bottom, targetPosition: Position.Right, position: position });
                    } else {
                        populatedNodes.push({ id: node, type: 'customNode', data: { title: node, instance_of: displayedNode['blocks'][node]['instance_of'], address: displayedNode['blocks'][node]['address'], type: displayedNode['blocks'][node]['type'], color: '#FFB703' }, sourcePosition: Position.Bottom, targetPosition: Position.Right, position: position });
                    }
                }
                // Assuming fetchedNodes is an array of nodes in the format expected by React Flow
                setNodes(populatedNodes);
                const populatedEdges = [];
                selected_links_data = {};
                for (const edge_id in displayedNode['harnesses']) {
                    const edge = displayedNode['harnesses'][edge_id];

                    // for each edge_id, update the data structure with the list of links on that harness
                    selected_links_data[edge_id] = {source: edge['source'], target: edge['target'], links: edge['links']};

                    // create a react edge element for each harness
                    populatedEdges.push({
                        id: edge_id,
                        source: edge['source'],
                        target: edge['target'],
                        type: 'custom',
                        sourcePosition: Position.Right,
                        targetPosition: Position.Left,
                        markerEnd: {
                            type: MarkerType.Arrow,
                        },
                        data: {
                            source: edge['source'],
                            target: edge['target'],
                            name: edge['name'],
                            preview_names: edge['preview_names'],
                        }
                    });
                }
                setEdges(populatedEdges);

            } catch (error) {
                console.error("Failed to fetch nodes:", error);
            }
        };

        updateNodesFromJson();
    }, [viewBlockId]);

    const onSelectionChange = (elements) => {
        // Filter out the selected edges from the selection
        const selectedEdge = elements['edges'][0];
        // check if there is a selected edge
        if (selectedEdge && !requestRelayout) {
            setSelectedLinkId(selectedEdge.id);
            setSelectedLinkData(selected_links_data[selectedEdge.id]['links']);
            setSelectedLinkSource(selected_links_data[selectedEdge.id]['source']);
            setSelectedLinkTarget(selected_links_data[selectedEdge.id]['target']);
        } else if (selected_link_id != "none") {
            setSelectedLinkId("none");
            setSelectedLinkData([]);
            setSelectedLinkSource("none");
            setSelectedLinkTarget("none");
        }
    };

    return (
    <div className="providerflow">
        <ReactFlow
            key={viewBlockId + "block"}
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
            <Panel position="top-right">
                <SimpleTable source={selected_link_source} target={selected_link_target} data={selected_link_data} />
            </Panel>
            <Background />
        </ReactFlow>
    </div>
    );
};


export const AtopileBlockDiagramApp = ({ savePos, handleLoad, reLayout, reLayoutCleared }) => {
    const { block_id } = useURLBlockID();
    return (
        <ReactFlowProvider>
            <AtopileBlockDiagram
                viewBlockId={block_id}
                savePos={savePos}
                handleLoad={handleLoad}
                reLayout={reLayout}
                reLayoutCleared={reLayoutCleared}
            />
        </ReactFlowProvider>
    );
}

export default AtopileBlockDiagramApp;
