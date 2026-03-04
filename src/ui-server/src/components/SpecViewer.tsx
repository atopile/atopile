/**
 * SpecViewer — read-only renderer for modules with has_requirement traits.
 *
 * Fetches spec data from the backend and renders:
 * 1. Header — module name + docstring
 * 2. Architecture diagram — React Flow graph from children + connections
 * 3. Requirements table — has_requirement traits + assert statements
 * 4. Sub-module drill-down — click a block for its details
 */

import { useEffect, useState, useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  type Node,
  type Edge,
  Position,
  Handle,
  MarkerType,
  BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

// ── Types ────────────────────────────────────────────────

interface Requirement {
  id: string;
  text: string;
  criteria: string;
  source: 'trait' | 'assert';
  status?: 'pass' | 'fail';
}

interface Assertion {
  text: string;
  status: 'pass' | 'fail' | 'unknown';
}

interface SpecChild {
  name: string;
  type: string;
  docstring: string | null;
}

interface Connection {
  from: string;
  to: string;
}

interface SpecModule {
  module: string;
  file: string;
  docstring: string | null;
  requirements: Requirement[];
  assertions: Assertion[];
  children: SpecChild[];
  connections: Connection[];
}

interface SpecsResponse {
  specs: SpecModule[];
}

// ── API ──────────────────────────────────────────────────

function getApiUrl(): string {
  const injected = (window as { __ATOPILE_API_URL__?: string }).__ATOPILE_API_URL__;
  if (injected) return injected;
  return '';
}

function getInjectedProjectRoot(): string {
  const injected = (window as { __ATOPILE_PROJECT_ROOT__?: string }).__ATOPILE_PROJECT_ROOT__;
  return injected || '';
}

async function resolveProjectRoot(): Promise<string> {
  const injected = getInjectedProjectRoot();
  if (injected) return injected;

  const apiUrl = getApiUrl();
  // Retry a few times — the backend may still be starting
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const resp = await fetch(`${apiUrl}/api/projects`);
      if (resp.ok) {
        const data = await resp.json();
        if (data.projects?.length > 0) {
          return data.projects[0].root;
        }
      }
    } catch {
      // Server may not be reachable yet — wait and retry
    }
    if (attempt < 2) await new Promise(r => setTimeout(r, 1500));
  }
  return '';
}

async function fetchSpecs(projectRoot?: string, target?: string): Promise<SpecsResponse> {
  const params = new URLSearchParams();
  if (projectRoot) params.set('project_root', projectRoot);
  params.set('target', target || 'default');

  const resp = await fetch(`${getApiUrl()}/api/specs?${params}`);
  if (!resp.ok) {
    const detail = await resp.text();
    throw new Error(`Failed to fetch specs: ${resp.status} ${detail}`);
  }
  return resp.json();
}

// ── Layout ───────────────────────────────────────────────

const NODE_W = 160;
const NODE_H = 52;
const GAP_X = 60;
const GAP_Y = 28;

/** Assign column depths via BFS from source nodes. */
function autoLayout(children: SpecChild[], connections: Connection[]) {
  const childNames = new Set(children.map(c => c.name));
  // Build adjacency from module-level connections
  const adj = new Map<string, Set<string>>();
  const inDeg = new Map<string, number>();
  for (const name of childNames) {
    adj.set(name, new Set());
    inDeg.set(name, 0);
  }

  const seen = new Set<string>();
  for (const conn of connections) {
    const from = conn.from.split('.')[0];
    const to = conn.to.split('.')[0];
    if (!childNames.has(from) || !childNames.has(to) || from === to) continue;
    const key = `${from}--${to}`;
    const rev = `${to}--${from}`;
    if (seen.has(key) || seen.has(rev)) continue;
    seen.add(key);
    adj.get(from)!.add(to);
    inDeg.set(to, (inDeg.get(to) || 0) + 1);
  }

  // Topological layers via Kahn's algorithm
  const depth = new Map<string, number>();
  const queue: string[] = [];
  for (const name of childNames) {
    if ((inDeg.get(name) || 0) === 0) {
      queue.push(name);
      depth.set(name, 0);
    }
  }
  while (queue.length) {
    const cur = queue.shift()!;
    const d = depth.get(cur)!;
    for (const next of adj.get(cur) || []) {
      const nd = Math.max(depth.get(next) ?? 0, d + 1);
      depth.set(next, nd);
      inDeg.set(next, (inDeg.get(next) || 1) - 1);
      if (inDeg.get(next) === 0) queue.push(next);
    }
  }

  // Assign unplaced nodes (cycles/isolated) to col 0
  for (const name of childNames) {
    if (!depth.has(name)) depth.set(name, 0);
  }

  // Group by column, then assign y positions
  const cols = new Map<number, string[]>();
  for (const [name, d] of depth) {
    if (!cols.has(d)) cols.set(d, []);
    cols.get(d)!.push(name);
  }

  const positions = new Map<string, { x: number; y: number }>();
  for (const [col, names] of cols) {
    const colHeight = names.length * (NODE_H + GAP_Y) - GAP_Y;
    const startY = -colHeight / 2;
    names.forEach((name, i) => {
      positions.set(name, {
        x: col * (NODE_W + GAP_X),
        y: startY + i * (NODE_H + GAP_Y),
      });
    });
  }

  return positions;
}

// ── Custom Node ──────────────────────────────────────────

interface ModuleNodeData {
  label: string;
  type: string;
  selected: boolean;
  [key: string]: unknown;
}

function ModuleNode({ data }: { data: ModuleNodeData }) {
  return (
    <div
      style={{
        background: data.selected ? '#2d5a8f' : '#2d4a6f',
        border: `1px solid ${data.selected ? '#6cb4ee' : '#4a7ab5'}`,
        padding: '6px 10px',
        minWidth: NODE_W - 20,
        color: '#ddd',
        fontSize: 12,
        fontFamily: 'var(--vscode-font-family, system-ui)',
        cursor: 'pointer',
        transition: 'border-color 0.15s, background 0.15s',
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: '#4a7ab5', width: 6, height: 6 }} />
      <div style={{ fontWeight: 600, fontSize: 12, marginBottom: 2, color: '#e0e0e0' }}>{data.label}</div>
      <div style={{ fontSize: 10, opacity: 0.55 }}>{data.type}</div>
      <Handle type="source" position={Position.Right} style={{ background: '#4a7ab5', width: 6, height: 6 }} />
    </div>
  );
}

const nodeTypes = { module: ModuleNode };

// ── Graph builder ────────────────────────────────────────

function buildFlowGraph(
  children: SpecChild[],
  connections: Connection[],
  selectedName: string | null,
): { nodes: Node[]; edges: Edge[] } {
  if (children.length === 0) return { nodes: [], edges: [] };

  const positions = autoLayout(children, connections);
  const childNames = new Set(children.map(c => c.name));

  const nodes: Node[] = children.map(child => ({
    id: child.name,
    type: 'module',
    position: positions.get(child.name) || { x: 0, y: 0 },
    data: {
      label: child.name,
      type: child.type,
      selected: child.name === selectedName,
    },
  }));

  const edgeSeen = new Set<string>();
  const edges: Edge[] = [];
  for (const conn of connections) {
    const from = conn.from.split('.')[0];
    const to = conn.to.split('.')[0];
    if (!childNames.has(from) || !childNames.has(to) || from === to) continue;
    const key = [from, to].sort().join('--');
    if (edgeSeen.has(key)) continue;
    edgeSeen.add(key);
    edges.push({
      id: key,
      source: from,
      target: to,
      type: 'smoothstep',
      animated: false,
      style: { stroke: '#4a7ab5', strokeWidth: 1.5 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#4a7ab5', width: 12, height: 12 },
    });
  }

  return { nodes, edges };
}

// ── Architecture Diagram ─────────────────────────────────

function ArchitectureDiagram({
  children,
  connections,
  onNodeClick,
  selectedName,
}: {
  children: SpecChild[];
  connections: Connection[];
  onNodeClick: (name: string) => void;
  selectedName: string | null;
}) {
  const { nodes, edges } = useMemo(
    () => buildFlowGraph(children, connections, selectedName),
    [children, connections, selectedName],
  );

  // Compute container height from node positions
  const height = useMemo(() => {
    if (nodes.length === 0) return 120;
    let minY = Infinity, maxY = -Infinity;
    for (const n of nodes) {
      minY = Math.min(minY, n.position.y);
      maxY = Math.max(maxY, n.position.y);
    }
    return Math.max(120, maxY - minY + NODE_H + 80);
  }, [nodes]);

  if (nodes.length === 0) return null;

  return (
    <div
      style={{
        height,
        background: '#1a1a2e',
        border: '1px solid var(--vscode-panel-border, #333)',
        marginBottom: 8,
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={(_ev, node) => onNodeClick(node.id)}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnDrag={true}
        zoomOnScroll={true}
        minZoom={0.3}
        maxZoom={2}
      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#333" />
      </ReactFlow>
    </div>
  );
}

// ── Components ───────────────────────────────────────────

function RequirementsTable({ requirements, assertions }: {
  requirements: Requirement[];
  assertions: Assertion[];
}) {
  const rows = useMemo(() => {
    const merged: Array<{
      id: string;
      text: string;
      criteria: string;
      verified: 'manual' | 'pass' | 'fail' | 'unknown';
    }> = [];

    for (const req of requirements) {
      merged.push({
        id: req.id,
        text: req.text,
        criteria: req.criteria,
        verified: 'manual',
      });
    }

    for (const [i, assertion] of assertions.entries()) {
      merged.push({
        id: `A${i + 1}`,
        text: assertion.text,
        criteria: 'auto-assert',
        verified: assertion.status,
      });
    }

    return merged;
  }, [requirements, assertions]);

  if (rows.length === 0) return null;

  return (
    <div className="sv-section">
      <div className="sv-section-title">Requirements</div>
      <table className="sv-table">
        <thead>
          <tr>
            <th style={{ width: '48px' }}>ID</th>
            <th>Requirement</th>
            <th>Criteria</th>
            <th style={{ width: '56px' }}>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td className="sv-mono">{row.id}</td>
              <td>{row.text}</td>
              <td className="sv-dim">{row.criteria}</td>
              <td className={`sv-mono sv-status sv-status--${row.verified}`}>
                {row.verified === 'manual' && '---'}
                {row.verified === 'pass' && 'PASS'}
                {row.verified === 'fail' && 'FAIL'}
                {row.verified === 'unknown' && '?'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ChildDetail({ child, onBack }: {
  child: SpecChild;
  onBack: () => void;
}) {
  return (
    <div className="sv-section sv-detail">
      <button className="sv-btn sv-btn--small" onClick={onBack}>Back</button>
      <div className="sv-detail-header">
        <span className="sv-detail-name">{child.name}</span>
        <span className="sv-dim">{child.type}</span>
      </div>
      {child.docstring && (
        <p className="sv-detail-doc">{child.docstring}</p>
      )}
    </div>
  );
}

function SpecCard({ spec, defaultExpanded }: { spec: SpecModule; defaultExpanded: boolean }) {
  const [selectedChild, setSelectedChild] = useState<SpecChild | null>(null);
  const [expanded, setExpanded] = useState(defaultExpanded);

  const hasChildren = spec.children.length > 0;
  const reqCount = spec.requirements.length + spec.assertions.length;
  const childCount = spec.children.length;

  const handleNodeClick = useCallback((name: string) => {
    const child = spec.children.find(c => c.name === name);
    if (child) setSelectedChild(child);
  }, [spec.children]);

  return (
    <div className="sv-card">
      <div className="sv-card-header" onClick={() => setExpanded(!expanded)}>
        <span className="sv-card-toggle">{expanded ? '\u25BC' : '\u25B6'}</span>
        <span className="sv-card-title">{spec.module}</span>
        <span className="sv-card-meta">
          {reqCount > 0 && (
            <span className="sv-tag sv-tag--req">{reqCount} req{reqCount !== 1 ? 's' : ''}</span>
          )}
          {childCount > 0 && (
            <span className="sv-tag sv-tag--child">{childCount} sub</span>
          )}
        </span>
        <span className="sv-dim sv-card-file">{spec.file}</span>
      </div>

      {expanded && (
        <div className="sv-card-body">
          {spec.docstring && (
            <p className="sv-docstring">{spec.docstring}</p>
          )}

          {selectedChild ? (
            <ChildDetail child={selectedChild} onBack={() => setSelectedChild(null)} />
          ) : hasChildren ? (
            <div className="sv-section">
              <div className="sv-section-title">Architecture</div>
              <ArchitectureDiagram
                children={spec.children}
                connections={spec.connections}
                onNodeClick={handleNodeClick}
                selectedName={selectedChild ? (selectedChild as SpecChild).name : null}
              />
            </div>
          ) : null}

          <RequirementsTable
            requirements={spec.requirements}
            assertions={spec.assertions}
          />
        </div>
      )}
    </div>
  );
}

// ── Main ─────────────────────────────────────────────────

export function SpecViewer() {
  const [specs, setSpecs] = useState<SpecModule[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadSpecs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const projectRoot = await resolveProjectRoot();
      if (!projectRoot) {
        setError(
          `No project root resolved. ` +
          `API URL: "${getApiUrl() || '(empty)'}". ` +
          `Injected root: "${getInjectedProjectRoot() || '(empty)'}". ` +
          `Make sure the atopile build server is running and a project is open.`
        );
        setSpecs([]);
        return;
      }
      const data = await fetchSpecs(projectRoot);
      setSpecs(data.specs);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSpecs();
  }, [loadSpecs]);

  return (
    <div className="sv">
      <div className="sv-toolbar">
        <span className="sv-toolbar-title">Specs</span>
        <button
          className="sv-btn"
          onClick={loadSpecs}
          disabled={loading}
        >
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div className="sv-error">{error}</div>
      )}

      {!loading && specs.length === 0 && !error && (
        <div className="sv-empty">
          <p>No requirements found.</p>
          <p className="sv-dim">
            Add <code>trait has_requirement&lt;id="R1", text="...", criteria="..."&gt;</code> to your modules.
          </p>
        </div>
      )}

      {specs.map((spec, i) => (
        <SpecCard
          key={`${spec.file}:${spec.module}`}
          spec={spec}
          defaultExpanded={i === 0}
        />
      ))}

      <style>{`
        .sv {
          padding: 0;
          font-family: var(--vscode-font-family, system-ui, -apple-system, sans-serif);
          font-size: 13px;
          color: var(--vscode-foreground, #ccc);
          background: var(--vscode-editor-background, #1e1e1e);
          min-height: 100vh;
          line-height: 1.45;
        }

        .sv-toolbar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 12px;
          border-bottom: 1px solid var(--vscode-panel-border, #333);
          position: sticky;
          top: 0;
          z-index: 10;
          background: var(--vscode-editor-background, #1e1e1e);
        }

        .sv-toolbar-title {
          font-weight: 600;
          font-size: 13px;
          text-transform: uppercase;
          letter-spacing: 0.6px;
          opacity: 0.7;
        }

        .sv-btn {
          padding: 3px 10px;
          border: 1px solid var(--vscode-button-border, #444);
          background: transparent;
          color: var(--vscode-foreground, #ccc);
          cursor: pointer;
          font-size: 11px;
        }
        .sv-btn:hover {
          background: var(--vscode-list-hoverBackground, #2a2d2e);
        }
        .sv-btn:disabled {
          opacity: 0.4;
          cursor: default;
        }
        .sv-btn--small {
          padding: 2px 8px;
          font-size: 11px;
          margin-bottom: 6px;
        }

        .sv-mono {
          font-family: var(--vscode-editor-font-family, 'Fira Code', monospace);
          font-size: 12px;
        }
        .sv-dim { opacity: 0.55; }

        .sv-error {
          padding: 8px 12px;
          background: var(--vscode-inputValidation-errorBackground, #5a1d1d);
          border-left: 3px solid var(--vscode-inputValidation-errorBorder, #be1100);
          margin: 8px 12px;
          font-size: 12px;
        }

        .sv-empty {
          padding: 40px 12px;
          text-align: center;
          opacity: 0.5;
        }
        .sv-empty code {
          background: var(--vscode-textCodeBlock-background, #2d2d2d);
          padding: 1px 5px;
          font-size: 11px;
        }

        .sv-card {
          border-bottom: 1px solid var(--vscode-panel-border, #333);
        }

        .sv-card-header {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          cursor: pointer;
          user-select: none;
        }
        .sv-card-header:hover {
          background: var(--vscode-list-hoverBackground, #2a2d2e);
        }

        .sv-card-toggle {
          font-size: 9px;
          width: 12px;
          flex-shrink: 0;
          opacity: 0.5;
        }

        .sv-card-title {
          font-weight: 600;
          font-size: 13px;
        }

        .sv-card-meta {
          display: flex;
          gap: 6px;
          align-items: center;
        }

        .sv-tag {
          font-size: 10px;
          padding: 1px 6px;
          font-weight: 500;
        }
        .sv-tag--req {
          color: #6cb4ee;
          border: 1px solid #3a6a8e;
        }
        .sv-tag--child {
          color: #8bc98b;
          border: 1px solid #3a6e3a;
        }

        .sv-card-file {
          font-size: 11px;
          margin-left: auto;
        }

        .sv-card-body {
          padding: 0 12px 12px 12px;
        }

        .sv-docstring {
          margin: 0 0 10px 0;
          font-size: 12px;
          opacity: 0.75;
          line-height: 1.5;
          padding-left: 12px;
          border-left: 2px solid var(--vscode-panel-border, #444);
        }

        .sv-section {
          margin-top: 10px;
        }

        .sv-section-title {
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          opacity: 0.5;
          margin-bottom: 6px;
        }

        .sv-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 12px;
        }

        .sv-table th {
          text-align: left;
          padding: 4px 8px;
          font-weight: 600;
          font-size: 10px;
          text-transform: uppercase;
          letter-spacing: 0.4px;
          opacity: 0.45;
          border-bottom: 1px solid var(--vscode-panel-border, #333);
        }

        .sv-table td {
          padding: 5px 8px;
          border-bottom: 1px solid var(--vscode-panel-border, #252525);
        }

        .sv-table tr:last-child td {
          border-bottom: none;
        }

        .sv-table tr:hover td {
          background: var(--vscode-list-hoverBackground, #2a2d2e);
        }

        .sv-status { font-weight: 600; }
        .sv-status--manual { opacity: 0.3; }
        .sv-status--pass { color: #73c991; }
        .sv-status--fail { color: #f14c4c; }
        .sv-status--unknown { opacity: 0.4; }

        .sv-detail {
          padding: 8px;
          border-left: 2px solid #4a7ab5;
          margin-left: 4px;
        }
        .sv-detail-header {
          display: flex;
          align-items: baseline;
          gap: 8px;
          margin-bottom: 4px;
        }
        .sv-detail-name {
          font-weight: 600;
        }
        .sv-detail-doc {
          margin: 0;
          font-size: 12px;
          opacity: 0.7;
          line-height: 1.5;
        }

        /* Override React Flow defaults for dark theme */
        .react-flow__pane {
          cursor: default !important;
        }
        .react-flow__node {
          cursor: pointer !important;
        }
        .react-flow__attribution {
          display: none !important;
        }
      `}</style>
    </div>
  );
}
