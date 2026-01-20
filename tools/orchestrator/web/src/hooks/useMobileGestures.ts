import { useState, useRef, useCallback } from 'react';

interface MobileGesturesConfig {
  enabled: boolean;
  onSwipeClose?: () => void;
  swipeThreshold?: number;
  maxSwipeOffset?: number;
}

interface MobileGesturesReturn {
  // Header visibility on scroll
  showMobileHeader: boolean;
  handleScroll: (e: React.UIEvent<HTMLDivElement>) => void;

  // Swipe to close
  swipeOffset: number;
  swipeOpacity: number;
  handleTouchStart: (e: React.TouchEvent) => void;
  handleTouchMove: (e: React.TouchEvent) => void;
  handleTouchEnd: () => void;

  // Style helpers
  getSwipeStyle: () => React.CSSProperties;
}

/**
 * Custom hook for mobile-specific gestures:
 * - Header visibility on scroll (show on scroll up, hide on scroll down)
 * - Swipe right to close
 */
export function useMobileGestures({
  enabled,
  onSwipeClose,
  swipeThreshold = 100,
  maxSwipeOffset = 200,
}: MobileGesturesConfig): MobileGesturesReturn {
  // Header visibility on scroll
  const [showMobileHeader, setShowMobileHeader] = useState(false);
  const lastScrollY = useRef(0);

  // Swipe to close
  const touchStartX = useRef(0);
  const touchStartY = useRef(0);
  const [swipeOffset, setSwipeOffset] = useState(0);
  const isSwipingRef = useRef(false);

  // Handle scroll to show/hide mobile header
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    if (!enabled) return;
    const currentScrollY = e.currentTarget.scrollTop;

    // Show header when scrolling up, hide when scrolling down
    if (currentScrollY < lastScrollY.current - 10) {
      setShowMobileHeader(true);
    } else if (currentScrollY > lastScrollY.current + 10) {
      setShowMobileHeader(false);
    }

    // Always show header at top
    if (currentScrollY < 20) {
      setShowMobileHeader(true);
    }

    lastScrollY.current = currentScrollY;
  }, [enabled]);

  // Touch handlers for swipe to close
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    if (!enabled || !onSwipeClose) return;
    touchStartX.current = e.touches[0].clientX;
    touchStartY.current = e.touches[0].clientY;
    isSwipingRef.current = false;
  }, [enabled, onSwipeClose]);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!enabled || !onSwipeClose) return;

    const deltaX = e.touches[0].clientX - touchStartX.current;
    const deltaY = e.touches[0].clientY - touchStartY.current;

    // Only swipe if horizontal movement is greater than vertical
    if (Math.abs(deltaX) > Math.abs(deltaY) && deltaX > 20) {
      isSwipingRef.current = true;
      // Only allow right swipe (positive deltaX)
      setSwipeOffset(Math.min(deltaX, maxSwipeOffset));
    }
  }, [enabled, onSwipeClose, maxSwipeOffset]);

  const handleTouchEnd = useCallback(() => {
    if (!enabled || !onSwipeClose) return;

    // If swiped more than threshold, close
    if (swipeOffset > swipeThreshold && isSwipingRef.current) {
      onSwipeClose();
    }

    setSwipeOffset(0);
    isSwipingRef.current = false;
  }, [enabled, onSwipeClose, swipeOffset, swipeThreshold]);

  // Calculate swipe opacity for visual feedback
  const swipeOpacity = enabled ? Math.max(0, 1 - swipeOffset / maxSwipeOffset) : 1;

  // Helper to get swipe-related inline styles
  const getSwipeStyle = useCallback((): React.CSSProperties => {
    if (!enabled || swipeOffset === 0) {
      return {};
    }
    return {
      transform: `translateX(${swipeOffset}px)`,
      opacity: swipeOpacity,
      transition: swipeOffset === 0 ? 'transform 0.2s ease-out, opacity 0.2s ease-out' : undefined,
    };
  }, [enabled, swipeOffset, swipeOpacity]);

  return {
    showMobileHeader,
    handleScroll,
    swipeOffset,
    swipeOpacity,
    handleTouchStart,
    handleTouchMove,
    handleTouchEnd,
    getSwipeStyle,
  };
}

export default useMobileGestures;
