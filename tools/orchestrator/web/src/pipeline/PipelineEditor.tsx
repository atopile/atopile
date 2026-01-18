import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
  BackgroundVariant,
  NodeChange,
  EdgeChange,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { usePipelineStore, useAgentStore } from '@/stores';
import { nodeTypes } from './nodes';
import { NodeConfigPanel } from './NodeConfigPanel';
import { AgentDetail } from '@/components/AgentDetail';
import type { PipelineNode, PipelineEdge } from '@/api/types';

// Convert pipeline nodes to React Flow nodes
function toFlowNodes(
  pipelineNodes: PipelineNode[],
  nodeStatus?: Record<string, string>,
  nodeAgentMap?: Record<string, string>,
  loopIterations?: Record<string, number>
): Node[] {
  return pipelineNodes.map((node) => ({
    id: node.id,
    type: node.type,
    position: node.position,
    data: {
      ...node.data as unknown as Record<string, unknown>,
      _nodeStatus: nodeStatus?.[node.id],
      _agentId: nodeAgentMap?.[node.id],
      _loopIteration: loopIterations?.[node.id],
    },
  }));
}

// Convert pipeline edges to React Flow edges
function toFlowEdges(pipelineEdges: PipelineEdge[]): Edge[] {
  return pipelineEdges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    sourceHandle: edge.source_handle ?? null,
    targetHandle: null,
    label: edge.label,
    animated: true,
    style: { stroke: '#6b7280' },
  }));
}

// Convert React Flow nodes back to pipeline nodes
function toPipelineNodes(flowNodes: Node[]): PipelineNode[] {
  return flowNodes.map((node) => ({
    id: node.id,
    type: node.type as PipelineNode['type'],
    position: node.position,
    data: node.data as unknown as PipelineNode['data'],
  }));
}

// Convert React Flow edges back to pipeline edges
function toPipelineEdges(flowEdges: Edge[]): PipelineEdge[] {
  return flowEdges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    source_handle: edge.sourceHandle ?? undefined,
    label: typeof edge.label === 'string' ? edge.label : undefined,
  }));
}

export function PipelineEditor() {
  const { editorNodes, editorEdges, setEditorNodes, setEditorEdges, getSelectedSession } = usePipelineStore();
  const { agents, fetchAgent } = useAgentStore();

  // Track external updates vs internal changes
  const isInternalChange = useRef(false);
  const lastExternalNodes = useRef<string>('');
  const lastExternalEdges = useRef<string>('');

  // Selected node for config panel
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Agent view mode (when viewing agent detail from pipeline)
  const [viewingAgentId, setViewingAgentId] = useState<string | null>(null);

  // Get the selected session for node status (only show status when a session is selected)
  const selectedSession = getSelectedSession();

  // Only show node status when a session is selected
  const nodeStatus = selectedSession?.node_status;
  const nodeAgentMap = selectedSession?.node_agent_map;
  const loopIterations = selectedSession?.loop_iterations;

  // Initialize React Flow state from store
  const [nodes, setNodes, onNodesChange] = useNodesState(
    toFlowNodes(editorNodes, nodeStatus, nodeAgentMap, loopIterations)
  );
  const [edges, setEdges, onEdgesChange] = useEdgesState(toFlowEdges(editorEdges));

  // Only sync from store when external changes occur (not from our own updates)
  useEffect(() => {
    const nodesJson = JSON.stringify(editorNodes);
    if (nodesJson !== lastExternalNodes.current && !isInternalChange.current) {
      lastExternalNodes.current = nodesJson;
      setNodes(toFlowNodes(editorNodes, nodeStatus, nodeAgentMap, loopIterations));
    }
    isInternalChange.current = false;
  }, [editorNodes, setNodes, nodeStatus, nodeAgentMap, loopIterations]);

  useEffect(() => {
    const edgesJson = JSON.stringify(editorEdges);
    if (edgesJson !== lastExternalEdges.current && !isInternalChange.current) {
      lastExternalEdges.current = edgesJson;
      setEdges(toFlowEdges(editorEdges));
    }
    isInternalChange.current = false;
  }, [editorEdges, setEdges]);

  // Handle all node changes (drag, select, etc.)
  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      onNodesChange(changes);

      // Check if any position changes occurred (drag)
      const hasPositionChange = changes.some(
        (change) => change.type === 'position' && change.position
      );

      if (hasPositionChange) {
        // Debounce the store update
        setTimeout(() => {
          setNodes((currentNodes) => {
            isInternalChange.current = true;
            lastExternalNodes.current = JSON.stringify(toPipelineNodes(currentNodes));
            setEditorNodes(toPipelineNodes(currentNodes));
            return currentNodes;
          });
        }, 0);
      }
    },
    [onNodesChange, setNodes, setEditorNodes]
  );

  // Handle edge changes
  const handleEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      onEdgesChange(changes);
    },
    [onEdgesChange]
  );

  // Handle edge connections
  const onConnect = useCallback(
    (params: Connection) => {
      const newEdge: Edge = {
        id: `e-${params.source}-${params.target}-${Date.now()}`,
        source: params.source || '',
        target: params.target || '',
        sourceHandle: params.sourceHandle ?? null,
        targetHandle: params.targetHandle ?? null,
        animated: true,
        style: { stroke: '#6b7280' },
      };
      setEdges((eds) => {
        const updated = addEdge(newEdge, eds);
        // Update store
        isInternalChange.current = true;
        lastExternalEdges.current = JSON.stringify(toPipelineEdges(updated));
        setEditorEdges(toPipelineEdges(updated));
        return updated;
      });
    },
    [setEdges, setEditorEdges]
  );

  // Handle edge deletion
  const onEdgesDelete = useCallback(
    (deletedEdges: Edge[]) => {
      const deletedIds = new Set(deletedEdges.map((e) => e.id));
      setEdges((eds) => {
        const remaining = eds.filter((e) => !deletedIds.has(e.id));
        isInternalChange.current = true;
        lastExternalEdges.current = JSON.stringify(toPipelineEdges(remaining));
        setEditorEdges(toPipelineEdges(remaining));
        return remaining;
      });
    },
    [setEdges, setEditorEdges]
  );

  // Handle node deletion
  const onNodesDelete = useCallback(
    (deletedNodes: Node[]) => {
      const deletedIds = new Set(deletedNodes.map((n) => n.id));

      setNodes((currentNodes) => {
        const remainingNodes = currentNodes.filter((n) => !deletedIds.has(n.id));
        isInternalChange.current = true;
        lastExternalNodes.current = JSON.stringify(toPipelineNodes(remainingNodes));
        setEditorNodes(toPipelineNodes(remainingNodes));
        return remainingNodes;
      });

      setEdges((currentEdges) => {
        const remainingEdges = currentEdges.filter(
          (e) => !deletedIds.has(e.source) && !deletedIds.has(e.target)
        );
        isInternalChange.current = true;
        lastExternalEdges.current = JSON.stringify(toPipelineEdges(remainingEdges));
        setEditorEdges(toPipelineEdges(remainingEdges));
        return remainingEdges;
      });
    },
    [setNodes, setEdges, setEditorNodes, setEditorEdges]
  );

  // Handle node double-click for config or agent view
  const onNodeDoubleClick = useCallback((_event: React.MouseEvent, node: Node) => {
    // For agent nodes with a running/completed agent, show agent detail
    if (node.type === 'agent') {
      // Use session's agent map if available, otherwise fall back to pipeline's
      const agentId = nodeAgentMap?.[node.id];
      if (agentId) {
        // Fetch agent data and show detail view
        fetchAgent(agentId);
        setViewingAgentId(agentId);
        return;
      }
    }
    // Otherwise, show config panel
    setSelectedNodeId(node.id);
  }, [nodeAgentMap, fetchAgent]);

  // Handle node selection
  const onSelectionChange = useCallback(({ nodes: selectedNodes }: { nodes: Node[] }) => {
    // Don't auto-open config on single click, only highlight
    if (selectedNodes.length === 1) {
      // Just track selection for potential double-click
    }
  }, []);

  // Update node data from config panel
  const handleNodeUpdate = useCallback(
    (nodeId: string, newData: Record<string, unknown>) => {
      setNodes((currentNodes) => {
        const updated = currentNodes.map((node) =>
          node.id === nodeId ? { ...node, data: newData } : node
        );
        isInternalChange.current = true;
        lastExternalNodes.current = JSON.stringify(toPipelineNodes(updated));
        setEditorNodes(toPipelineNodes(updated));
        return updated;
      });
    },
    [setNodes, setEditorNodes]
  );

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);
  const viewingAgent = viewingAgentId ? agents.get(viewingAgentId) : null;

  return (
    <div className="h-full w-full flex">
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={handleNodesChange}
          onEdgesChange={handleEdgesChange}
          onConnect={onConnect}
          onNodesDelete={onNodesDelete}
          onEdgesDelete={onEdgesDelete}
          onNodeDoubleClick={onNodeDoubleClick}
          onSelectionChange={onSelectionChange}
          nodeTypes={nodeTypes}
          fitView
          deleteKeyCode="Delete"
          className="bg-gray-900"
          nodesDraggable={true}
          nodesConnectable={true}
          elementsSelectable={true}
          selectNodesOnDrag={false}
        >
          <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#374151" />
          <Controls className="!bg-gray-800 !border-gray-700 !rounded-lg" />
          <MiniMap
            nodeColor={(node) => {
              switch (node.type) {
                case 'agent':
                  return '#22c55e';
                case 'trigger':
                  return '#3b82f6';
                case 'loop':
                  return '#a855f7';
                case 'condition':
                  return '#eab308';
                default:
                  return '#6b7280';
              }
            }}
            className="!bg-gray-800 !border-gray-700 !rounded-lg"
          />
        </ReactFlow>
      </div>

      {/* Node Config Panel */}
      {selectedNode && !viewingAgent && (
        <NodeConfigPanel
          node={selectedNode}
          onUpdate={handleNodeUpdate}
          onClose={() => setSelectedNodeId(null)}
        />
      )}

      {/* Agent Detail Panel (when viewing agent from pipeline node) */}
      {viewingAgent && (
        <div className="w-[500px] border-l border-gray-700 bg-gray-800 flex flex-col">
          <AgentDetail
            agent={viewingAgent}
            onClose={() => setViewingAgentId(null)}
          />
        </div>
      )}
    </div>
  );
}

export default PipelineEditor;
