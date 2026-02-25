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
  bodyFill: string;
  bodyBorder: string;
  pinPower: string;
  pinGround: string;
  pinI2C: string;
  pinSPI: string;
  pinUART: string;
  pinReset: string;
  pinSignal: string;
  netElectrical: string;
  pinNC: string;
  pinCrystal: string;
  pinAnalog: string;
  busI2C: string;
  busSPI: string;
  busUART: string;
}

// ── Domain colors (no VSCode equivalent) ────────────────────────

const DOMAIN_DARK = {
  bodyFill: '#121826',
  bodyBorder: '#4a5a7a',
  pinPower: '#f38ba8',
  pinGround: '#a6adc8',
  pinI2C: '#89b4fa',
  pinSPI: '#cba6f7',
  pinUART: '#a6e3a1',
  pinReset: '#fab387',
  pinSignal: '#94e2d5',
  netElectrical: '#7f8ea8',
  pinNC: '#585b70',
  pinCrystal: '#f9e2af',
  pinAnalog: '#fab387',
  busI2C: '#89b4fa',
  busSPI: '#cba6f7',
  busUART: '#a6e3a1',
};

const DOMAIN_LIGHT = {
  bodyFill: '#f4f7fc',
  bodyBorder: '#a8b4cc',
  pinPower: '#d84d73',
  pinGround: '#6d768a',
  pinI2C: '#2e74d2',
  pinSPI: '#7c4dcf',
  pinUART: '#2f8f52',
  pinReset: '#c47733',
  pinSignal: '#1e8d97',
  netElectrical: '#5e6f92',
  pinNC: '#9aa3b8',
  pinCrystal: '#b08b1f',
  pinAnalog: '#bc6f2a',
  busI2C: '#2e74d2',
  busSPI: '#7c4dcf',
  busUART: '#2f8f52',
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

// ── Utilities ───────────────────────────────────────────────────

export function getPinColor(category: string, theme: ThemeColors): string {
  switch ((category || '').toLowerCase()) {
    case 'power':
      return theme.pinPower;
    case 'ground':
      return theme.pinGround;
    case 'i2c':
      return theme.pinI2C;
    case 'spi':
      return theme.pinSPI;
    case 'uart':
      return theme.pinUART;
    case 'reset':
      return theme.pinReset;
    case 'crystal':
      return theme.pinCrystal;
    case 'analog':
      return theme.pinAnalog;
    case 'nc':
      return theme.pinNC;
    case 'electrical':
      return theme.netElectrical;
    default:
      return theme.pinSignal;
  }
}

function colorLuminance(hex: string): number {
  const value = hex.replace('#', '');
  if (value.length !== 6) return 0;
  const r = parseInt(value.slice(0, 2), 16) / 255;
  const g = parseInt(value.slice(2, 4), 16) / 255;
  const b = parseInt(value.slice(4, 6), 16) / 255;
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function isThemeLight(theme: ThemeColors): boolean {
  return colorLuminance(theme.bgPrimary) > 0.5;
}
