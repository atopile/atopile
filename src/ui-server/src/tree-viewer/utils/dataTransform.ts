import type {
  I2CTreeData,
  PowerTreeData,
  TreeEdge,
  TreeGraphData,
  TreeNode,
} from '../types/tree';

function clean(value: string | null | undefined, fallback = '?'): string {
  const v = (value ?? '').trim();
  return v.length > 0 ? v : fallback;
}

function compactId(value: string): string {
  return value.replace(/[^a-zA-Z0-9:_-]/g, '_');
}

export function powerTreeToGraph(data: PowerTreeData): TreeGraphData {
  const nodes: TreeNode[] = data.nodes.map((n) => ({
    id: n.id,
    type: n.type,
    label: n.name,
    sublabel: n.voltage_out || n.voltage || undefined,
    group: n.parent_module || undefined,
    groupLabel: n.parent_module || undefined,
    meta: {
      voltage: clean(n.voltage),
      voltage_in: clean(n.voltage_in),
      voltage_out: clean(n.voltage_out),
      max_current: clean(n.max_current),
    },
  }));

  const edges: TreeEdge[] = data.edges.map((e, idx) => ({
    id: `pwr:${idx}:${compactId(e.from)}->${compactId(e.to)}`,
    source: e.from,
    target: e.to,
  }));

  return { nodes, edges };
}

export function i2cTreeToGraph(data: I2CTreeData): TreeGraphData {
  const nodes: TreeNode[] = [];
  const edges: TreeEdge[] = [];

  for (const bus of data.buses) {
    const busId = `i2c:${compactId(bus.id)}`;

    for (const ctrl of bus.controllers) {
      nodes.push({
        id: ctrl.id,
        type: 'controller',
        label: ctrl.name,
        sublabel: bus.frequency || undefined,
        group: ctrl.parent_module || undefined,
        groupLabel: ctrl.parent_module || undefined,
        meta: {
          bus_frequency: clean(bus.frequency),
        },
      });

      for (const target of bus.targets) {
        const targetId = `${busId}:target:${compactId(target.id)}`;
        const existing = nodes.find((n) => n.id === targetId);
        if (!existing) {
          nodes.push({
            id: targetId,
            type: 'target',
            label: target.name,
            resolved: target.address_resolved,
            sublabel: target.address || undefined,
            group: target.parent_module || undefined,
            groupLabel: target.parent_module || undefined,
            meta: {
              address: clean(target.address),
              bus: bus.id,
            },
          });
        }

        edges.push({
          id: `i2c:${compactId(ctrl.id)}->${compactId(targetId)}`,
          source: ctrl.id,
          target: targetId,
        });
      }
    }
  }

  return { nodes, edges };
}
