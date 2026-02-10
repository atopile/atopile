import type { ThemeColors } from '../lib/theme';
import { getStandardInterfaceColor } from '../../interfaceColors';

const SEMANTIC_CONNECTION_COLORS: Readonly<Record<string, string>> = {
  power: '#ce8ea1',
  ground: '#9aa4b8',
  reset: '#c9ad7a',
  control: '#c9ad7a',
  analog: '#c3a68d',
  crystal: '#b5bbd3',
};

export function neutralConnectionColor(theme: ThemeColors): string {
  return theme.textMuted;
}

export function getSemanticConnectionColor(
  raw: string | null | undefined,
): string | null {
  if (!raw) return null;
  const normalized = raw.trim().toLowerCase();
  if (!normalized) return null;
  return getStandardInterfaceColor(normalized) || SEMANTIC_CONNECTION_COLORS[normalized] || null;
}

export function getConnectionColor(
  raw: string | null | undefined,
  theme: ThemeColors,
): string {
  return getSemanticConnectionColor(raw) || neutralConnectionColor(theme);
}
