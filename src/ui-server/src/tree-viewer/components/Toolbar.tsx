import { useTreeStore } from '../stores/treeStore';
import { useTheme } from '../utils/theme';
import type { ViewerMode } from '../types/tree';

export function Toolbar() {
  const { mode } = useTreeStore();
  const theme = useTheme();

  const modeLabel: Record<ViewerMode, string> = {
    power: 'Power Tree',
    i2c: 'I2C Tree',
  };

  const modeIcon: Record<ViewerMode, string> = {
    power: '\u26A1',
    i2c: '\u2261',
  };

  return (
    <div
      style={{
        height: 36,
        display: 'flex',
        alignItems: 'center',
        padding: '0 12px',
        gap: 8,
        background: theme.bgSecondary,
        borderBottom: `1px solid ${theme.borderColor}`,
      }}
    >
      <span style={{ fontSize: 14, color: theme.accent }}>
        {modeIcon[mode]}
      </span>
      <h1
        style={{
          margin: 0,
          fontWeight: 500,
          fontSize: 12,
          letterSpacing: '0.05em',
          color: theme.textPrimary,
        }}
      >
        {modeLabel[mode]}
      </h1>
      <div style={{ flex: 1 }} />
      <span style={{ fontSize: 12, color: theme.textMuted }}>
        atopile
      </span>
    </div>
  );
}
