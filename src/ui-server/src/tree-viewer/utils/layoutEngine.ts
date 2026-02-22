import type { TreeGraphData } from '../types/tree';

export interface NodePosition {
  x: number;
  y: number;
  z: number;
  width: number;
  height: number;
}

export interface LayoutResult {
  positions: Map<string, NodePosition>;
  bounds: {
    minX: number;
    minY: number;
    maxX: number;
    maxY: number;
  };
}

function nodeSize(type: string): { width: number; height: number } {
  if (type === 'source') return { width: 170, height: 78 };
  if (type === 'converter' || type === 'controller') return { width: 188, height: 82 };
  if (type === 'target') return { width: 170, height: 70 };
  return { width: 164, height: 72 };
}

export function computeTreeLayout(graph: TreeGraphData): LayoutResult {
  const positions = new Map<string, NodePosition>();
  const outgoing = new Map<string, string[]>();
  const incoming = new Map<string, string[]>();

  for (const n of graph.nodes) {
    outgoing.set(n.id, []);
    incoming.set(n.id, []);
  }
  for (const e of graph.edges) {
    outgoing.get(e.source)?.push(e.target);
    incoming.get(e.target)?.push(e.source);
  }

  const ranks = new Map<string, number>();
  const queue: string[] = [];

  const sources = graph.nodes.filter((n) => (incoming.get(n.id)?.length ?? 0) === 0);
  const starters = sources.length > 0 ? sources : graph.nodes.slice(0, 1);
  for (const node of starters) {
    ranks.set(node.id, 0);
    queue.push(node.id);
  }

  // First-discovery BFS rank assignment is stable for cyclic graphs.
  while (queue.length > 0) {
    const id = queue.shift()!;
    const r = ranks.get(id) ?? 0;
    for (const nxt of outgoing.get(id) ?? []) {
      if (!ranks.has(nxt)) {
        ranks.set(nxt, r + 1);
        queue.push(nxt);
      }
    }
  }

  for (const node of graph.nodes) {
    if (!ranks.has(node.id)) ranks.set(node.id, 0);
  }

  const columns = new Map<number, string[]>();
  for (const node of graph.nodes) {
    const r = ranks.get(node.id) ?? 0;
    const col = columns.get(r) ?? [];
    col.push(node.id);
    columns.set(r, col);
  }

  for (const [rank, ids] of columns.entries()) {
    ids.sort((a, b) => a.localeCompare(b));
    for (let i = 0; i < ids.length; i++) {
      const id = ids[i];
      const node = graph.nodes.find((n) => n.id === id)!;
      const size = nodeSize(node.type);
      positions.set(id, {
        x: rank * 230,
        y: -i * 140,
        z: 0,
        width: size.width,
        height: size.height,
      });
    }
  }

  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;

  for (const pos of positions.values()) {
    minX = Math.min(minX, pos.x - pos.width / 2);
    maxX = Math.max(maxX, pos.x + pos.width / 2);
    minY = Math.min(minY, pos.y - pos.height / 2);
    maxY = Math.max(maxY, pos.y + pos.height / 2);
  }

  if (!Number.isFinite(minX)) {
    minX = minY = maxX = maxY = 0;
  }

  return {
    positions,
    bounds: { minX, minY, maxX, maxY },
  };
}
