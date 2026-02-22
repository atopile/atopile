import { useTreeStore } from '../stores/treeStore';
import { useTheme } from '../utils/theme';
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
    <div style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{
        fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.05em',
        marginBottom: 8, color: theme.textMuted,
      }}>
        Legend
      </div>
      {items.map((item) => (
        <div key={item.type} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
          <span
            style={{
              width: 10, height: 10, borderRadius: 2, display: 'inline-block',
              backgroundColor: theme[item.colorKey] as string,
            }}
          />
          <span style={{ color: theme.textPrimary }}>{item.label}</span>
        </div>
      ))}
    </div>
  );
}
