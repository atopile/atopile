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
import { PANEL_CONFIGS, PANEL_IDS, type PanelId } from '../utils/panelConfig';

// Constants - must match CSS .section-title-bar height
const TITLE_BAR_HEIGHT = 26; // Height of each panel's title bar (matches native VS Code/Cursor sidebar items)
const MIN_BODY_HEIGHT = 60; // Fallback minimum for panel body (content area)

interface PanelState {
  collapsed: boolean;
  userHeight?: number; // Set when user manually resizes (includes title bar)
}

interface UsePanelSizingOptions {
  containerRef: React.RefObject<HTMLElement>;
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
  collapseAllExceptProjects: () => void;
  handleResizeStart: (panelId: PanelId, e: React.MouseEvent) => void;
  isCollapsed: (panelId: PanelId) => boolean;
}

function getInitialState(): Record<PanelId, PanelState> {
  const state: Partial<Record<PanelId, PanelState>> = {};
  for (const id of PANEL_IDS) {
    state[id] = { collapsed: id !== 'projects' };
  }
  return state as Record<PanelId, PanelState>;
}

function clampBodyHeight(panelId: PanelId, bodyHeight: number): number {
  const maxHeight = PANEL_CONFIGS[panelId]?.maxHeight;
  if (!maxHeight) {
    return bodyHeight;
  }
  return Math.min(bodyHeight, maxHeight);
}

function getMinBodyHeight(panelId: PanelId): number {
  return PANEL_CONFIGS[panelId]?.minHeight ?? MIN_BODY_HEIGHT;
}

function getPreferredBodyHeight(panelId: PanelId): number {
  return PANEL_CONFIGS[panelId]?.preferredHeight ?? getMinBodyHeight(panelId);
}

export function usePanelSizing(options: UsePanelSizingOptions): UsePanelSizingReturn {
  const {
    containerRef,
    hasProjectSelected = false,
  } = options;

  const [panelStates, setPanelStates] = useState<Record<PanelId, PanelState>>(getInitialState);
  const [priorityPanel, setPriorityPanel] = useState<PanelId | null>('projects');
  const [containerHeight, setContainerHeight] = useState(0);

  // Track previous values for auto-expand
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
    let autoSizedPanels = expandedPanels.filter(id => panelStates[id].userHeight === undefined);

    // Calculate space used by user-sized panels (userHeight includes title bar, so subtract it)
    let userSizedSpace = 0;
    for (const id of userSizedPanels) {
      const userHeight = panelStates[id].userHeight!;
      const bodyHeight = userHeight - TITLE_BAR_HEIGHT;
      heights[id] = userHeight;
      userSizedSpace += bodyHeight;
    }

    // Reserve preferred height for projects when another panel is prioritized
    let reservedSpace = 0;
    if (
      autoSizedPanels.includes('projects') &&
      priorityPanel &&
      priorityPanel !== 'projects' &&
      expandedPanels.length > 1
    ) {
      const preferred = clampBodyHeight('projects', getPreferredBodyHeight('projects'));
      const availableAfterUser = Math.max(0, availableForBodies - userSizedSpace);
      const reservedBody = Math.min(preferred, availableAfterUser);
      heights.projects = reservedBody + TITLE_BAR_HEIGHT;
      reservedSpace = reservedBody;
      autoSizedPanels = autoSizedPanels.filter(id => id !== 'projects');
    }

    // Remaining space for auto-sized panels
    const remainingSpace = Math.max(0, availableForBodies - userSizedSpace - reservedSpace);

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
      const allowBeyondMax =
        (expandedPanels.length === 1 && id === 'projects') ||
        (expandedPanels.length === 2 && id !== 'projects' && expandedPanels.includes('projects'));
      const bodyHeight = allowBeyondMax
        ? Math.max(getMinBodyHeight(id), remainingSpace)
        : clampBodyHeight(id, Math.max(getMinBodyHeight(id), remainingSpace));
      heights[id] = bodyHeight + TITLE_BAR_HEIGHT;
    } else if (priorityInAuto) {
      // Multiple auto-sized panels with a priority panel
      // Non-priority panels get minimum, priority gets the rest
      const nonPriorityPanels = autoSizedPanels.filter(id => id !== priorityPanel);
      const nonPrioritySpace = nonPriorityPanels.reduce((sum, id) => sum + getMinBodyHeight(id), 0);
      const priorityMin = priorityPanel ? getMinBodyHeight(priorityPanel) : MIN_BODY_HEIGHT;
      const prioritySpace = Math.max(priorityMin, remainingSpace - nonPrioritySpace);

      for (const id of autoSizedPanels) {
        if (id === priorityPanel) {
          const bodyHeight = clampBodyHeight(id, prioritySpace);
          heights[id] = bodyHeight + TITLE_BAR_HEIGHT;
        } else {
          const bodyHeight = clampBodyHeight(id, getMinBodyHeight(id));
          heights[id] = bodyHeight + TITLE_BAR_HEIGHT;
        }
      }
    } else {
      // Multiple auto-sized panels, no priority among them
      // Distribute space equally
      const spacePerPanel = remainingSpace / autoSizedPanels.length;
      for (const id of autoSizedPanels) {
        const bodyHeight = clampBodyHeight(id, Math.max(getMinBodyHeight(id), spacePerPanel));
        heights[id] = bodyHeight + TITLE_BAR_HEIGHT;
      }
    }

    return heights;
  }, [containerHeight, panelStates, priorityPanel]);

  // Toggle panel
  const togglePanel = useCallback((panelId: PanelId) => {
    setPanelStates(prev => {
      const willExpand = prev[panelId].collapsed;
      const newState = { ...prev };

      if (willExpand && panelId !== 'projects') {
        for (const id of PANEL_IDS) {
          if (id !== 'projects' && id !== panelId) {
            newState[id] = { ...newState[id], collapsed: true, userHeight: undefined };
          }
        }
      }

      newState[panelId] = {
        ...newState[panelId],
        collapsed: !newState[panelId].collapsed,
        // Clear userHeight when collapsing (fresh start on re-expand)
        userHeight: willExpand ? newState[panelId].userHeight : undefined,
      };

      if (panelId === 'projects') {
        if (willExpand) {
          setPriorityPanel('projects');
        } else {
          const nextPriority = PANEL_IDS.find(id => !newState[id].collapsed) ?? null;
          setPriorityPanel(nextPriority);
        }
      } else if (willExpand) {
        setPriorityPanel(panelId);
      } else if (!newState.projects?.collapsed) {
        setPriorityPanel('projects');
      }
      return newState;
    });
  }, []);

  // Expand panel
  const expandPanel = useCallback((panelId: PanelId) => {
    setPanelStates(prev => {
      const nextState = { ...prev };

      if (panelId !== 'projects') {
        for (const id of PANEL_IDS) {
          if (id !== 'projects' && id !== panelId) {
            nextState[id] = { ...nextState[id], collapsed: true, userHeight: undefined };
          }
        }
      }

      nextState[panelId] = { ...nextState[panelId], collapsed: false };

      if (panelId === 'projects') {
        setPriorityPanel('projects');
      } else {
        setPriorityPanel(panelId);
      }
      return nextState;
    });
  }, []);

  // Collapse panel
  const collapsePanel = useCallback((panelId: PanelId) => {
    setPanelStates(prev => {
      const nextState = {
        ...prev,
        [panelId]: { ...prev[panelId], collapsed: true, userHeight: undefined },
      };
      if (panelId === 'projects') {
        const nextPriority = PANEL_IDS.find(id => !nextState[id].collapsed) ?? null;
        setPriorityPanel(nextPriority);
      } else if (priorityPanel === panelId) {
        if (!nextState.projects?.collapsed) {
          setPriorityPanel('projects');
        } else {
          const nextPriority = PANEL_IDS.find(id => !nextState[id].collapsed) ?? null;
          setPriorityPanel(nextPriority);
        }
      }
      return nextState;
    });
  }, [priorityPanel]);

  // Collapse all panels except projects (used when starting a build)
  const collapseAllExceptProjects = useCallback(() => {
    setPanelStates(prev => {
      const nextState = { ...prev };
      for (const id of PANEL_IDS) {
        if (id !== 'projects') {
          nextState[id] = { ...nextState[id], collapsed: true, userHeight: undefined };
        }
      }
      // Ensure projects is expanded
      nextState.projects = { ...nextState.projects, collapsed: false };
      return nextState;
    });
    setPriorityPanel('projects');
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
    collapseAllExceptProjects,
    handleResizeStart,
    isCollapsed,
  };
}
