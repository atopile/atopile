import { useState, useEffect, useCallback } from 'react';

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
  warning: string;
  error: string;
  nodeSource: string;
  nodeSink: string;
  nodeBus: string;
  nodeController: string;
  nodeTarget: string;
}

// ── Domain colors (no VSCode equivalent) ────────────────────────

const DOMAIN_DARK = {
  nodeSource: '#89b4fa',
  nodeSink: '#f38ba8',
  nodeBus: '#cba6f7',
  nodeController: '#94e2d5',
  nodeTarget: '#a6e3a1',
};

const DOMAIN_LIGHT = {
  nodeSource: '#2e74d2',
  nodeSink: '#d84d73',
  nodeBus: '#7c4dcf',
  nodeController: '#1e8d97',
  nodeTarget: '#2f8f52',
};

// ── Theme detection ─────────────────────────────────────────────

export function detectThemeMode(): 'light' | 'dark' {
  if (typeof document === 'undefined') return 'dark';
  if (document.body.classList.contains('vscode-light')) return 'light';
  if (document.body.classList.contains('vscode-high-contrast-light')) return 'light';
  if (document.body.classList.contains('vscode-dark')) return 'dark';
  if (document.body.classList.contains('vscode-high-contrast')) return 'dark';
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

function readCSSColor(varName: string, fallback: string): string {
  if (typeof document === 'undefined') return fallback;
  const value = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  return value || fallback;
}

// ── CSS var fallbacks (Catppuccin Mocha dark / Latte light) ─────

const CSS_FALLBACKS = {
  dark: {
    bgPrimary: '#1e1e2e',
    bgSecondary: '#181825',
    bgTertiary: '#313244',
    bgHover: '#45475a',
    textPrimary: '#cdd6f4',
    textSecondary: '#bac2de',
    textMuted: '#7f849c',
    borderColor: '#45475a',
    borderSubtle: '#313244',
    accent: '#f95015',
    warning: '#f9e2af',
    error: '#f38ba8',
  },
  light: {
    bgPrimary: '#eff1f5',
    bgSecondary: '#e6e9ef',
    bgTertiary: '#ccd0da',
    bgHover: '#bcc0cc',
    textPrimary: '#4c4f69',
    textSecondary: '#5c5f77',
    textMuted: '#8c8fa1',
    borderColor: '#bcc0cc',
    borderSubtle: '#ccd0da',
    accent: '#d94410',
    warning: '#df8e1d',
    error: '#d20f39',
  },
};

function resolveTheme(mode: 'light' | 'dark'): ThemeColors {
  const fb = CSS_FALLBACKS[mode];
  const domain = mode === 'light' ? DOMAIN_LIGHT : DOMAIN_DARK;

  return {
    bgPrimary: readCSSColor('--bg-primary', fb.bgPrimary),
    bgSecondary: readCSSColor('--bg-secondary', fb.bgSecondary),
    bgTertiary: readCSSColor('--bg-tertiary', fb.bgTertiary),
    bgHover: readCSSColor('--bg-hover', fb.bgHover),
    textPrimary: readCSSColor('--text-primary', fb.textPrimary),
    textSecondary: readCSSColor('--text-secondary', fb.textSecondary),
    textMuted: readCSSColor('--text-muted', fb.textMuted),
    borderColor: readCSSColor('--border-color', fb.borderColor),
    borderSubtle: readCSSColor('--border-subtle', fb.borderSubtle),
    accent: readCSSColor('--accent', fb.accent),
    warning: readCSSColor('--warning', fb.warning),
    error: readCSSColor('--error', fb.error),
    ...domain,
  };
}

// ── React hook ──────────────────────────────────────────────────

export function useTheme(): ThemeColors {
  const [theme, setTheme] = useState<ThemeColors>(() => resolveTheme(detectThemeMode()));

  const refresh = useCallback(() => {
    setTheme(resolveTheme(detectThemeMode()));
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Watch body class mutations (VSCode theme changes)
    const observer = new MutationObserver(refresh);
    observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });

    // Watch prefers-color-scheme (dev mode)
    const mql = window.matchMedia('(prefers-color-scheme: light)');
    mql.addEventListener('change', refresh);

    return () => {
      observer.disconnect();
      mql.removeEventListener('change', refresh);
    };
  }, [refresh]);

  return theme;
}
