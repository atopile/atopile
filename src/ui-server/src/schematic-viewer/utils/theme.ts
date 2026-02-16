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

function isLightPreferred(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-color-scheme: light)').matches;
}

export function useTheme(): ThemeColors {
  return useMemo(() => (isLightPreferred() ? LIGHT : DARK), []);
}

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
