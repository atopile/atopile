import { useMemo } from 'react';

export interface ThemeColors {
  bgPrimary: string;
  bgSecondary: string;
  bgTertiary: string;
  bgHover: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  borderColor: string;
  borderSubtle: string;
  accent: string;
  nodeSource: string;
  nodeSink: string;
  nodeBus: string;
  nodeController: string;
  nodeTarget: string;
}

const DARK: ThemeColors = {
  bgPrimary: '#0f1115',
  bgSecondary: '#151923',
  bgTertiary: '#1c2230',
  bgHover: '#262f42',
  textPrimary: '#e9ecf3',
  textSecondary: '#bdc5d6',
  textMuted: '#8b95aa',
  borderColor: '#31384a',
  borderSubtle: '#252c3d',
  accent: '#4ea1ff',
  nodeSource: '#89b4fa',
  nodeSink: '#f38ba8',
  nodeBus: '#cba6f7',
  nodeController: '#94e2d5',
  nodeTarget: '#a6e3a1',
};

const LIGHT: ThemeColors = {
  bgPrimary: '#f7f8fb',
  bgSecondary: '#ffffff',
  bgTertiary: '#eef1f7',
  bgHover: '#e4e8f2',
  textPrimary: '#1d2433',
  textSecondary: '#3a445a',
  textMuted: '#67708a',
  borderColor: '#c8d0e0',
  borderSubtle: '#d9dfeb',
  accent: '#1d6fd6',
  nodeSource: '#2e74d2',
  nodeSink: '#d84d73',
  nodeBus: '#7c4dcf',
  nodeController: '#1e8d97',
  nodeTarget: '#2f8f52',
};

function isLightPreferred(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-color-scheme: light)').matches;
}

export function useTheme(): ThemeColors {
  return useMemo(() => (isLightPreferred() ? LIGHT : DARK), []);
}
