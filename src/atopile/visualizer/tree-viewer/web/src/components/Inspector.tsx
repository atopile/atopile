import { useTreeStore } from '../stores/treeStore';
import { useTheme } from '../lib/theme';

const WARN_COLOR = '#f9e2af';
const WARN_BG = 'rgba(249, 226, 175, 0.08)';

function getWarning(node: { type: string; resolved?: boolean; meta?: Record<string, string> }): string | null {
  if (node.resolved === false) return 'Address unresolved — device may not communicate on the bus';
  return null;
}

export function Inspector() {
  const { graphData, selectedNode } = useTreeStore();
  const theme = useTheme();

  if (!graphData || !selectedNode) {
    return (
      <div className="p-3 text-xs" style={{ color: theme.textMuted }}>
        Click a node to inspect
      </div>
    );
  }

  const node = graphData.nodes.find((n) => n.id === selectedNode);
  if (!node) return null;

  const warning = getWarning(node);

  return (
    <div className="p-3 space-y-2">
      {/* Warning banner (if any) */}
      {warning && (
        <div
          className="flex items-start gap-2 p-2 rounded text-xs"
          style={{
            background: WARN_BG,
            border: `1px solid ${WARN_COLOR}33`,
          }}
        >
          <span style={{ color: WARN_COLOR, fontSize: 14, lineHeight: 1 }}>{'\u26A0'}</span>
          <span style={{ color: WARN_COLOR, lineHeight: 1.4 }}>{warning}</span>
        </div>
      )}

      {/* Node info */}
      <div>
        <div className="text-xs uppercase tracking-wider mb-1" style={{ color: theme.textMuted, fontSize: 10 }}>
          {node.type}
        </div>
        <div className="text-sm font-semibold" style={{ color: theme.textPrimary }}>
          {node.label}
        </div>
        {node.sublabel && (
          <div className="text-xs mt-0.5" style={{ color: theme.textSecondary }}>
            {node.sublabel}
          </div>
        )}
      </div>

      {/* Properties */}
      {node.meta && Object.keys(node.meta).length > 0 && (
        <div className="pt-2 space-y-1.5" style={{ borderTop: `1px solid ${theme.borderColor}` }}>
          {Object.entries(node.meta).map(([key, value]) => (
            <div key={key} className="flex justify-between text-xs">
              <span style={{ color: theme.textMuted }}>{key}</span>
              <span className="font-mono" style={{ color: theme.textPrimary }}>
                {value}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Address resolved status */}
      {node.resolved !== undefined && (
        <div className="pt-2" style={{ borderTop: `1px solid ${theme.borderColor}` }}>
          <div className="flex items-center gap-1.5 text-xs">
            <span
              className="w-1.5 h-1.5 rounded-full inline-block"
              style={{ backgroundColor: node.resolved ? theme.nodeSource : WARN_COLOR }}
            />
            <span style={{ color: node.resolved ? theme.textMuted : WARN_COLOR }}>
              {node.resolved ? 'Address resolved' : 'Address unresolved'}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
