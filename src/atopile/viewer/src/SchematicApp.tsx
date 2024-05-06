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
    const response = await fetch('http://127.0.0.1:8080/data');
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
}

const block_id = "root";
const parent_block_addr = "none";
const selected_link_data = [];
const selected_link_source = "none";
const selected_link_target = "none";
const requestRelayout = false;
let selected_links_data = {};


const AtopileViewer = () => {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [requestRelayout, setRequestRelayout] = useState(false);
    const { fitView } = useReactFlow();
    const [block_id, setBlockId] = useState("root");
    const [parent_block_addr, setParentBlockAddr] = useState("none");
    const [selected_link_id, setSelectedLinkId] = useState("none");
    const [selected_link_data, setSelectedLinkData] = useState([]);
    const [selected_link_source, setSelectedLinkSource] = useState("none");
    const [selected_link_target, setSelectedLinkTarget] = useState("none");

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
                        populatedNodes.push({ id: signal_name, type: 'Signal', data: signal_data , position: position });
                        console.log(signal_name);
                    }
                }
                // Assuming fetchedNodes is an array of nodes in the format expected by React Flow
                setNodes(populatedNodes);
                const populatedEdges = [];
                selected_links_data = {};
                for (const edge of fetchedNodes['links']) {
                    // create a react edge element for each harness
                    populatedEdges.push({
                        id: edge['source']['component'] + edge['target']['component'],
                        source: edge['source']['component'],
                        sourceHandle: edge['source']['port'],
                        target: edge['target']['component'],
                        targetHandle: edge['target']['port'],
                        type: 'step',
                        style: {
                            stroke: 'black',
                            strokeWidth: 2,
                        },
                    });
                }
                setEdges(populatedEdges);

                // Request a re-layout
                setRequestRelayout(true);
            } catch (error) {
                console.error("Failed to fetch nodes:", error);
            }
        };

        updateNodesFromJson();
    }, [block_id]);

    // Calculate the initial layout on mount.
    useLayoutEffect(() => {
        if (requestRelayout) {
            onLayout({ direction: 'RIGHT' });
            console.log('Relayout requested');
            setRequestRelayout(false);
        }
    }, [edges]);

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
        <Panel position="top-right">
            <SimpleTable source={selected_link_source} target={selected_link_target} data={selected_link_data} />
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