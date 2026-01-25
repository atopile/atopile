/**
 * useTheme hook - Manages theme preference (dark/light/system)
 *
 * - Persists preference to localStorage
 * - Applies data-theme attribute to document root
 * - Listens for system preference changes when in "system" mode
 */

import { useCallback, useEffect, useState } from 'react';

export type ThemePreference = 'dark' | 'light' | 'system';

const STORAGE_KEY = 'atopile-theme-preference';

function getStoredTheme(): ThemePreference {
  if (typeof window === 'undefined') return 'system';
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'dark' || stored === 'light' || stored === 'system') {
    return stored;
  }
  return 'system';
}

function getSystemTheme(): 'dark' | 'light' {
  if (typeof window === 'undefined') return 'dark';
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

export function useTheme() {
  const [theme, setThemeState] = useState<ThemePreference>(getStoredTheme);
  const [resolvedTheme, setResolvedTheme] = useState<'dark' | 'light'>(() => {
    const pref = getStoredTheme();
    return pref === 'system' ? getSystemTheme() : pref;
  });

  // Apply theme to document
  const applyTheme = useCallback((preference: ThemePreference) => {
    const root = document.documentElement;
    root.setAttribute('data-theme', preference);

    // Update resolved theme
    const resolved = preference === 'system' ? getSystemTheme() : preference;
    setResolvedTheme(resolved);
  }, []);

  // Set theme preference
  const setTheme = useCallback((newTheme: ThemePreference) => {
    setThemeState(newTheme);
    localStorage.setItem(STORAGE_KEY, newTheme);
    applyTheme(newTheme);
  }, [applyTheme]);

  // Initialize theme on mount
  useEffect(() => {
    applyTheme(theme);
  }, [applyTheme, theme]);

  // Listen for system preference changes
  useEffect(() => {
    if (theme !== 'system') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: light)');

    const handleChange = () => {
      setResolvedTheme(getSystemTheme());
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [theme]);

  return {
    theme,           // Current preference: 'dark' | 'light' | 'system'
    resolvedTheme,   // Actual applied theme: 'dark' | 'light'
    setTheme,        // Function to change theme
    isDark: resolvedTheme === 'dark',
    isLight: resolvedTheme === 'light',
  };
}

// Export a function to initialize theme before React hydrates
// This prevents flash of wrong theme
export function initializeTheme() {
  if (typeof window === 'undefined') return;

  const preference = getStoredTheme();
  document.documentElement.setAttribute('data-theme', preference);
}
