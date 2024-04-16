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
} from 'reactflow';
import 'reactflow/dist/style.css';

import { createNodesAndEdges } from './utils.js';
import { CustomNodeBlock, CircularNodeComponent } from './CustomNode';
import CustomEdge from './CustomEdge';

import SimpleTable from './link-table';

import './index.css';

import ELK from 'elkjs/lib/elk.bundled.js';

const { nodes: initialNodes, edges: initialEdges } = createNodesAndEdges();


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
  customNode: CustomNodeBlock, // Register your custom node type
  customCircularNode: CircularNodeComponent
};

const edgeTypes = {
  custom: CustomEdge,
};

async function loadJsonAsDict() {
  const response = await fetch('http://127.0.0.1:8080/data');
  if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
}

const block_id = "root";
const parent_block_addr = "none";


const NodeAsHandleFlow = () => {
    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
    const { fitView } = useReactFlow();
    const [block_id, setBlockId] = useState("root");
    const [parent_block_addr, setParentBlockAddr] = useState("none");

    // const onConnect = useCallback(
    // (params) =>
    //     setEdges((eds) =>
    //     addEdge({ ...params, type: 'default', markerEnd: { type: MarkerType.Arrow } }, eds)
    //     ),
    // [setEdges]
    // );

    const handleExpandClick = (newBlockId) => {
        setBlockId(newBlockId);
    };

    const onLayout = useCallback(
    ({ direction, useInitialNodes = false }) => {
        const opts = { 'elk.direction': direction, ...elkOptions };
        const ns = useInitialNodes ? initialNodes : nodes;
        const es = useInitialNodes ? initialEdges : edges;

        getLayoutedElements(ns, es, opts).then(({ nodes: layoutedNodes, edges: layoutedEdges }) => {
        setNodes(layoutedNodes);
        setEdges(layoutedEdges);

        window.requestAnimationFrame(() => fitView());
        });
    },
    [nodes, edges]
    );


    useEffect(() => {
    const updateNodesFromJson = async () => {
        try {
        const fetchedNodes = await loadJsonAsDict();
        const displayedNode = fetchedNodes[block_id];
        setParentBlockAddr(displayedNode['parent']);
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
                populatedNodes.push({ id: node, type: 'customNode', data: { title: node, instance_of: displayedNode['blocks'][node]['instance_of'], address: displayedNode['blocks'][node]['address'], type: displayedNode['blocks'][node]['type'], color: '#FB8500', handleExpandClick: handleExpandClick }, sourcePosition: Position.Bottom, targetPosition: Position.Right, position: position });
            } else {
                populatedNodes.push({ id: node, type: 'customNode', data: { title: node, instance_of: displayedNode['blocks'][node]['instance_of'], address: displayedNode['blocks'][node]['address'], type: displayedNode['blocks'][node]['type'], color: '#FFB703', handleExpandClick: handleExpandClick }, sourcePosition: Position.Bottom, targetPosition: Position.Right, position: position });
            }
        }
        // Assuming fetchedNodes is an array of nodes in the format expected by React Flow
        setNodes(populatedNodes);
        const populatedEdges = [];
        for (const edge of displayedNode['links']) {
            populatedEdges.push({
                id: `${edge['source']['block']}${edge['source']['port']}-${edge['target']['block']}${edge['target']['port']}`,
                source: edge['source']['block'],
                target: edge['target']['block'],
                type: 'custom',
                sourcePosition: Position.Right,
                targetPosition: Position.Left,
                markerEnd: {
                    type: MarkerType.Arrow,
                },
                data: {
                    source: edge['source']['port'],
                    target: edge['target']['port'],
                    instance_of: edge['instance_of']
                }
            });
        }
        setEdges(populatedEdges);
        } catch (error) {
        console.error("Failed to fetch nodes:", error);
        }
    };

    updateNodesFromJson();
    }, [block_id]);

    // Calculate the initial layout on mount.
    useLayoutEffect(() => {
        onLayout({ direction: 'DOWN' });
    }, [edges]);

    return (
    <div className="floatingedges">
        <ReactFlow
        key={block_id}
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        //onConnect={onConnect}
        fitView
        edgeTypes={edgeTypes}
        nodeTypes={nodeTypes}
        >
        <Panel position="top-left">
            <div style={{backgroundColor: 'lightgray', border: '2px solid grey', margin: '10px', padding: '10px', borderRadius: '10px'}}>
                <div style={{textAlign: 'center'}}> Model inspection pane</div>
                <div><i>Inspecting:</i> <b>{block_id}</b></div>
                <div><i>Parent:</i> {parent_block_addr}</div>
                <button onClick={() => handleExpandClick(parent_block_addr)}>return</button>
            </div>
        </Panel>
        <Panel position="top-right">
            <SimpleTable />
        </Panel>
        <Background />
        </ReactFlow>
    </div>
    );
};

// export default NodeAsHandleFlow;

export default () => (
  <ReactFlowProvider>
    <NodeAsHandleFlow />
  </ReactFlowProvider>
);
