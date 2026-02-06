import { useTreeStore } from '../stores/treeStore';
import { useTheme } from '../lib/theme';
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
      className="h-9 flex items-center px-3 gap-2"
      style={{
        background: theme.bgSecondary,
        borderBottom: `1px solid ${theme.borderColor}`,
      }}
    >
      <span className="text-sm" style={{ color: theme.accent }}>
        {modeIcon[mode]}
      </span>
      <h1
        className="font-medium text-xs tracking-wide"
        style={{ color: theme.textPrimary }}
      >
        {modeLabel[mode]}
      </h1>
      <div className="flex-1" />
      <span className="text-xs" style={{ color: theme.textMuted }}>
        atopile
      </span>
    </div>
  );
}
