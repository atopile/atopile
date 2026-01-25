/**
 * Unified Panel Sizing Hook
 *
 * Implements panel behavior invariants:
 * 1. All headers always visible
 * 2. Priority panel (last expanded) gets most space
 * 3. Content scrolls, never clips
 * 4. Manual resize wins
 * 5. Collapse reclaims space immediately
 * 6. Predictable expansion behavior
 * 7. Minimum viable height for expanded panels
 */

import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { PANEL_IDS, type PanelId } from '../utils/panelConfig';

// Constants
const TITLE_BAR_HEIGHT = 32; // Height of each panel's title bar
const MIN_BODY_HEIGHT = 60; // Minimum height for panel body (content area)

interface PanelState {
  collapsed: boolean;
  userHeight?: number; // Set when user manually resizes (includes title bar)
}

interface UsePanelSizingOptions {
  containerRef: React.RefObject<HTMLElement>;
  hasActiveBuilds?: boolean;
  hasProjectSelected?: boolean;
}

interface CalculatedHeights {
  [key: string]: number | undefined;
}

interface UsePanelSizingReturn {
  panelStates: Record<PanelId, PanelState>;
  priorityPanel: PanelId | null;
  calculatedHeights: CalculatedHeights;
  togglePanel: (panelId: PanelId) => void;
  expandPanel: (panelId: PanelId) => void;
  collapsePanel: (panelId: PanelId) => void;
  handleResizeStart: (panelId: PanelId, e: React.MouseEvent) => void;
  isCollapsed: (panelId: PanelId) => boolean;
}

function getInitialState(): Record<PanelId, PanelState> {
  const state: Partial<Record<PanelId, PanelState>> = {};
  for (const id of PANEL_IDS) {
    state[id] = { collapsed: true };
  }
  return state as Record<PanelId, PanelState>;
}

export function usePanelSizing(options: UsePanelSizingOptions): UsePanelSizingReturn {
  const {
    containerRef,
    hasActiveBuilds = false,
    hasProjectSelected = false,
  } = options;

  const [panelStates, setPanelStates] = useState<Record<PanelId, PanelState>>(getInitialState);
  const [priorityPanel, setPriorityPanel] = useState<PanelId | null>(null);
  const [containerHeight, setContainerHeight] = useState(0);

  // Track previous values for auto-expand
  const prevHasActiveBuilds = useRef(hasActiveBuilds);
  const prevHasProjectSelected = useRef(hasProjectSelected);

  // Resize drag refs
  const resizingRef = useRef<PanelId | null>(null);
  const startYRef = useRef(0);
  const startHeightRef = useRef(0);
  const rafRef = useRef<number | null>(null);

  // Observe container size changes
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const updateHeight = () => {
      setContainerHeight(container.clientHeight);
    };

    updateHeight();

    const observer = new ResizeObserver(updateHeight);
    observer.observe(container);

    return () => observer.disconnect();
  }, [containerRef]);

  // Auto-expand: Build Queue when builds start
  useEffect(() => {
    if (hasActiveBuilds && !prevHasActiveBuilds.current) {
      setPanelStates(prev => ({
        ...prev,
        buildQueue: { ...prev.buildQueue, collapsed: false },
      }));
      setPriorityPanel('buildQueue');
    }
    prevHasActiveBuilds.current = hasActiveBuilds;
  }, [hasActiveBuilds]);

  // Auto-expand: Projects when a project is selected
  useEffect(() => {
    if (hasProjectSelected && !prevHasProjectSelected.current) {
      setPanelStates(prev => ({
        ...prev,
        projects: { ...prev.projects, collapsed: false },
      }));
      setPriorityPanel('projects');
    }
    prevHasProjectSelected.current = hasProjectSelected;
  }, [hasProjectSelected]);

  // Calculate heights based on invariants
  const calculatedHeights = useMemo((): CalculatedHeights => {
    const heights: CalculatedHeights = {};

    if (containerHeight === 0) {
      // Container not measured yet, return undefined heights (use CSS defaults)
      return heights;
    }

    // Get list of expanded panels
    const expandedPanels = PANEL_IDS.filter(id => !panelStates[id].collapsed);

    // Calculate available space for panel bodies
    // Total space minus all title bars (every panel always shows its title bar)
    const totalTitleBarSpace = PANEL_IDS.length * TITLE_BAR_HEIGHT;
    const availableForBodies = containerHeight - totalTitleBarSpace;

    if (expandedPanels.length === 0) {
      // All collapsed - no body heights needed
      return heights;
    }

    // Panels with user-set heights
    const userSizedPanels = expandedPanels.filter(id => panelStates[id].userHeight !== undefined);
    const autoSizedPanels = expandedPanels.filter(id => panelStates[id].userHeight === undefined);

    // Calculate space used by user-sized panels (userHeight includes title bar, so subtract it)
    let userSizedSpace = 0;
    for (const id of userSizedPanels) {
      const userHeight = panelStates[id].userHeight!;
      const bodyHeight = userHeight - TITLE_BAR_HEIGHT;
      heights[id] = userHeight;
      userSizedSpace += bodyHeight;
    }

    // Remaining space for auto-sized panels
    const remainingSpace = Math.max(0, availableForBodies - userSizedSpace);

    if (autoSizedPanels.length === 0) {
      // All expanded panels are user-sized
      return heights;
    }

    // Distribute remaining space among auto-sized panels
    // Priority panel gets the lion's share, others get minimum
    const priorityInAuto = priorityPanel && autoSizedPanels.includes(priorityPanel);

    if (autoSizedPanels.length === 1) {
      // Only one auto-sized panel - it gets all remaining space
      const id = autoSizedPanels[0];
      const bodyHeight = Math.max(MIN_BODY_HEIGHT, remainingSpace);
      heights[id] = bodyHeight + TITLE_BAR_HEIGHT;
    } else if (priorityInAuto) {
      // Multiple auto-sized panels with a priority panel
      // Non-priority panels get minimum, priority gets the rest
      const nonPriorityCount = autoSizedPanels.length - 1;
      const nonPrioritySpace = nonPriorityCount * MIN_BODY_HEIGHT;
      const prioritySpace = Math.max(MIN_BODY_HEIGHT, remainingSpace - nonPrioritySpace);

      for (const id of autoSizedPanels) {
        if (id === priorityPanel) {
          heights[id] = prioritySpace + TITLE_BAR_HEIGHT;
        } else {
          heights[id] = MIN_BODY_HEIGHT + TITLE_BAR_HEIGHT;
        }
      }
    } else {
      // Multiple auto-sized panels, no priority among them
      // Distribute space equally
      const spacePerPanel = Math.max(MIN_BODY_HEIGHT, remainingSpace / autoSizedPanels.length);
      for (const id of autoSizedPanels) {
        heights[id] = spacePerPanel + TITLE_BAR_HEIGHT;
      }
    }

    return heights;
  }, [containerHeight, panelStates, priorityPanel]);

  // Toggle panel
  const togglePanel = useCallback((panelId: PanelId) => {
    setPanelStates(prev => {
      const willExpand = prev[panelId].collapsed;
      const newState = {
        ...prev,
        [panelId]: {
          ...prev[panelId],
          collapsed: !prev[panelId].collapsed,
          // Clear userHeight when collapsing (fresh start on re-expand)
          userHeight: willExpand ? prev[panelId].userHeight : undefined,
        },
      };
      if (willExpand) {
        setPriorityPanel(panelId);
      }
      return newState;
    });
  }, []);

  // Expand panel
  const expandPanel = useCallback((panelId: PanelId) => {
    setPanelStates(prev => ({
      ...prev,
      [panelId]: { ...prev[panelId], collapsed: false },
    }));
    setPriorityPanel(panelId);
  }, []);

  // Collapse panel
  const collapsePanel = useCallback((panelId: PanelId) => {
    setPanelStates(prev => ({
      ...prev,
      [panelId]: { ...prev[panelId], collapsed: true, userHeight: undefined },
    }));
  }, []);

  // Resize handlers
  const handleResizeMove = useCallback((e: MouseEvent) => {
    if (!resizingRef.current) return;

    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
    }

    rafRef.current = requestAnimationFrame(() => {
      const panelId = resizingRef.current!;
      const delta = e.clientY - startYRef.current;
      const newHeight = Math.max(
        TITLE_BAR_HEIGHT + MIN_BODY_HEIGHT,
        startHeightRef.current + delta
      );

      setPanelStates(prev => ({
        ...prev,
        [panelId]: { ...prev[panelId], userHeight: newHeight },
      }));
      rafRef.current = null;
    });
  }, []);

  const handleResizeEnd = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    resizingRef.current = null;
    document.body.classList.remove('resizing');
    document.removeEventListener('mousemove', handleResizeMove);
    document.removeEventListener('mouseup', handleResizeEnd);
  }, [handleResizeMove]);

  const handleResizeStart = useCallback((panelId: PanelId, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    resizingRef.current = panelId;
    startYRef.current = e.clientY;

    // Get current height from calculated or DOM
    const currentHeight = calculatedHeights[panelId];
    if (currentHeight) {
      startHeightRef.current = currentHeight;
    } else {
      const section = (e.target as HTMLElement).closest('.collapsible-section');
      startHeightRef.current = section?.getBoundingClientRect().height ?? 200;
    }

    document.body.classList.add('resizing');
    document.addEventListener('mousemove', handleResizeMove);
    document.addEventListener('mouseup', handleResizeEnd);
  }, [calculatedHeights, handleResizeMove, handleResizeEnd]);

  const isCollapsed = useCallback((panelId: PanelId): boolean => {
    return panelStates[panelId]?.collapsed ?? true;
  }, [panelStates]);

  return {
    panelStates,
    priorityPanel,
    calculatedHeights,
    togglePanel,
    expandPanel,
    collapsePanel,
    handleResizeStart,
    isCollapsed,
  };
}
