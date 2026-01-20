import { useState, useEffect } from 'react';

/**
 * Hook to detect mobile viewport
 * @param breakpoint - Width threshold in pixels (default: 768)
 * @returns boolean indicating if viewport is mobile-sized
 */
export function useMobile(breakpoint = 768): boolean {
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth < breakpoint;
  });

  useEffect(() => {
    const mediaQuery = window.matchMedia(`(max-width: ${breakpoint - 1}px)`);

    const handleChange = (e: MediaQueryListEvent | MediaQueryList) => {
      setIsMobile(e.matches);
    };

    // Set initial value
    handleChange(mediaQuery);

    // Listen for changes
    mediaQuery.addEventListener('change', handleChange);

    return () => {
      mediaQuery.removeEventListener('change', handleChange);
    };
  }, [breakpoint]);

  return isMobile;
}
