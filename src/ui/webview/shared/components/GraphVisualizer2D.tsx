import {
  ReactFlow,
  BaseEdge,
  EdgeLabelRenderer,
  getStraightPath,
  Handle,
  Position,
  type Node,
  type Edge,
  type NodeProps,
  type EdgeProps,
  type NodeChange,
  type ReactFlowInstance,
} from '@xyflow/react'
import { useCallback, useEffect, useRef, useState } from 'react'
import './GraphVisualizer2D.css'

/* ── Public API types ── */

export interface GraphNode {
  id: string
  label: string
  subtitle?: string
  x: number
  y: number
}

export interface GraphEdge {
  id: string
  from: string
  to: string
  label?: string
  sublabel?: string
  color?: string
}

/* ── Custom node ── */

const centerHandle: React.CSSProperties = {
  left: '50%',
  top: '50%',
  transform: 'translate(-50%, -50%)',
}

function GraphNodeComponent({ data }: NodeProps) {
  const subtitle = data.subtitle as string | undefined
  return (
    <div className="graph-node">
      <Handle type="target" position={Position.Left} style={centerHandle} />
      <div>{data.label as string}</div>
      {subtitle && <div className="graph-node-subtitle">{subtitle}</div>}
      <Handle type="source" position={Position.Right} style={centerHandle} />
    </div>
  )
}

/* ── Custom edge ── */

function GraphEdgeComponent({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  data,
}: EdgeProps) {
  const label = data?.label as string | undefined
  const sublabel = data?.sublabel as string | undefined
  const color = (data?.color as string | undefined) ?? 'var(--text-muted)'

  const [edgePath, labelX, labelY] = getStraightPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
  })

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{ stroke: color }}
      />
      {label && (
        <EdgeLabelRenderer>
          <div
            className="graph-edge-label"
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              pointerEvents: 'none',
              color,
            }}
          >
            {label}
            {sublabel && <span className="graph-edge-sublabel">{sublabel}</span>}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  )
}

/* ── Node / edge type registries (must be outside component) ── */

const nodeTypes = { graph: GraphNodeComponent }
const edgeTypes = { graph: GraphEdgeComponent }

/* ── Main component ── */

export function GraphVisualizer2D({
  nodes,
  edges,
  height = 200,
}: {
  nodes: GraphNode[]
  edges: GraphEdge[]
  height?: number
}) {
  // Track measured dimensions from React Flow's ResizeObserver.
  // Without this, controlled-mode re-renders overwrite the internal
  // measured state and edges lose their anchor points.
  const [measured, setMeasured] = useState<
    Record<string, { width: number; height: number }>
  >({})

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    const updates: Record<string, { width: number; height: number }> = {}
    let hasUpdates = false
    for (const change of changes) {
      if (change.type === 'dimensions' && change.dimensions) {
        updates[change.id] = change.dimensions
        hasUpdates = true
      }
    }
    if (hasUpdates) {
      setMeasured((prev) => ({ ...prev, ...updates }))
    }
  }, [])

  const rfNodes: Node[] = nodes.map((n) => ({
    id: n.id,
    type: 'graph',
    position: { x: n.x, y: n.y },
    data: { label: n.label, subtitle: n.subtitle },
    measured: measured[n.id] ?? { width: 120, height: 32 },
  }))

  const rfEdges: Edge[] = edges.map((e) => ({
    id: e.id,
    type: 'graph',
    source: e.from,
    target: e.to,
    data: { label: e.label, sublabel: e.sublabel, color: e.color },
  }))

  const instanceRef = useRef<ReactFlowInstance | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const onInit = useCallback((instance: ReactFlowInstance) => {
    instanceRef.current = instance
    instance.fitView({ padding: 0.2 })
  }, [])

  // Re-fit on container resize
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const observer = new ResizeObserver(() => {
      instanceRef.current?.fitView({ padding: 0.2 })
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  return (
    <div ref={containerRef} className="graph-visualizer" style={{ height }}>
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        onNodesChange={onNodesChange}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnScroll={false}
        zoomOnScroll={false}
        zoomOnPinch={false}
        zoomOnDoubleClick={false}
        preventScrolling={false}
        panOnDrag={false}
        proOptions={{ hideAttribution: true }}
        fitView
        onInit={onInit}
      />
    </div>
  )
}
