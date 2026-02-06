import { useTreeStore } from '../stores/treeStore';
import { useTheme } from '../lib/theme';
import type { TreeNodeType } from '../types/tree';

interface LegendItem { type: TreeNodeType; label: string; colorKey: keyof ReturnType<typeof useTheme> }

const POWER_ITEMS: LegendItem[] = [
  { type: 'source', label: 'Power Source', colorKey: 'nodeSource' },
  { type: 'converter', label: 'Converter', colorKey: 'nodeBus' },
  { type: 'sink', label: 'Load', colorKey: 'nodeSink' },
];

const I2C_ITEMS: LegendItem[] = [
  { type: 'controller', label: 'Controller', colorKey: 'nodeController' },
  { type: 'target', label: 'Target', colorKey: 'nodeTarget' },
];

export function Legend() {
  const { mode } = useTreeStore();
  const theme = useTheme();
  const items = mode === 'power' ? POWER_ITEMS : I2C_ITEMS;

  return (
    <div className="p-3 space-y-1.5">
      <div className="text-xs uppercase tracking-wider mb-2" style={{ color: theme.textMuted, fontSize: 10 }}>
        Legend
      </div>
      {items.map((item) => (
        <div key={item.type} className="flex items-center gap-1.5 text-xs">
          <span
            className="w-2.5 h-2.5 rounded-sm inline-block"
            style={{ backgroundColor: theme[item.colorKey] as string }}
          />
          <span style={{ color: theme.textPrimary }}>{item.label}</span>
        </div>
      ))}
    </div>
  );
}
