import { useTreeStore } from '../stores/treeStore';
import { useTheme } from '../utils/theme';

function getWarning(node: { type: string; resolved?: boolean; meta?: Record<string, string> }): string | null {
  if (node.resolved === false) return 'Address unresolved — device may not communicate on the bus';
  return null;
}

export function Inspector() {
  const { graphData, selectedNode } = useTreeStore();
  const theme = useTheme();

  if (!graphData || !selectedNode) {
    return (
      <div style={{ padding: 12, fontSize: 12, color: theme.textMuted }}>
        Click a node to inspect
      </div>
    );
  }

  const node = graphData.nodes.find((n) => n.id === selectedNode);
  if (!node) return null;

  const warning = getWarning(node);

  return (
    <div style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
      {/* Warning banner (if any) */}
      {warning && (
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: 8,
            padding: 8,
            borderRadius: 4,
            fontSize: 12,
            background: `${theme.warning}14`,
            border: `1px solid ${theme.warning}33`,
          }}
        >
          <span style={{ color: theme.warning, fontSize: 14, lineHeight: 1 }}>{'\u26A0'}</span>
          <span style={{ color: theme.warning, lineHeight: 1.4 }}>{warning}</span>
        </div>
      )}

      {/* Node info */}
      <div>
        <div style={{
          fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.05em',
          marginBottom: 4, color: theme.textMuted,
        }}>
          {node.type}
        </div>
        <div style={{ fontSize: 14, fontWeight: 600, color: theme.textPrimary }}>
          {node.label}
        </div>
        {node.sublabel && (
          <div style={{ fontSize: 12, marginTop: 2, color: theme.textSecondary }}>
            {node.sublabel}
          </div>
        )}
      </div>

      {/* Properties */}
      {node.meta && Object.keys(node.meta).length > 0 && (
        <div style={{
          paddingTop: 8, borderTop: `1px solid ${theme.borderColor}`,
          display: 'flex', flexDirection: 'column', gap: 6,
        }}>
          {Object.entries(node.meta).map(([key, value]) => (
            <div key={key} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
              <span style={{ color: theme.textMuted }}>{key}</span>
              <span style={{ fontFamily: 'var(--font-mono, monospace)', color: theme.textPrimary }}>
                {value}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Address resolved status */}
      {node.resolved !== undefined && (
        <div style={{ paddingTop: 8, borderTop: `1px solid ${theme.borderColor}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
            <span
              style={{
                width: 6, height: 6, borderRadius: '50%', display: 'inline-block',
                backgroundColor: node.resolved ? theme.nodeSource : theme.warning,
              }}
            />
            <span style={{ color: node.resolved ? theme.textMuted : theme.warning }}>
              {node.resolved ? 'Address resolved' : 'Address unresolved'}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
