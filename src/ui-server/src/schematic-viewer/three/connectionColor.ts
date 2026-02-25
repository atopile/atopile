import type { ThemeColors } from '../utils/theme';
import { isThemeLight } from '../utils/theme';
import { getStandardInterfaceColor } from '../../interfaceColors';

const SEMANTIC_DARK: Readonly<Record<string, string>> = {
  power: '#ce8ea1',
  ground: '#9aa4b8',
  reset: '#c9ad7a',
  control: '#c9ad7a',
  analog: '#c3a68d',
  crystal: '#b5bbd3',
};

const SEMANTIC_LIGHT: Readonly<Record<string, string>> = {
  power: '#b24066',
  ground: '#626a80',
  reset: '#9a7e3c',
  control: '#9a7e3c',
  analog: '#8e6e4e',
  crystal: '#6b7290',
};

export function neutralConnectionColor(theme: ThemeColors): string {
  return theme.textMuted;
}

export function getSemanticConnectionColor(
  raw: string | null | undefined,
  theme: ThemeColors,
): string | null {
  if (!raw) return null;
  const normalized = raw.trim().toLowerCase();
  if (!normalized) return null;
  const light = isThemeLight(theme);
  const palette = light ? SEMANTIC_LIGHT : SEMANTIC_DARK;
  return getStandardInterfaceColor(normalized, light) || palette[normalized] || null;
}

export function getConnectionColor(
  raw: string | null | undefined,
  theme: ThemeColors,
): string {
  return getSemanticConnectionColor(raw, theme) || neutralConnectionColor(theme);
}
