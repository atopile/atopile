/**
 * Sidebar Effects Hook
 * Handles all useEffect logic for the Sidebar component
 */

import { useEffect, useRef } from 'react';
import { api } from '../../api/client';
import { useStore } from '../../store';

interface UseSidebarEffectsProps {
  selectedProjectRoot: string | null;
  selectedTargetName: string | null;
  collapsedSections: Set<string>;
  sectionHeights: Record<string, number>;
  setSectionHeights: React.Dispatch<React.SetStateAction<Record<string, number>>>;
  setCollapsedSections: React.Dispatch<React.SetStateAction<Set<string>>>;
  containerRef: React.RefObject<HTMLDivElement>;
  action: (name: string, data?: Record<string, unknown>) => void;
}

export function useSidebarEffects({
  selectedProjectRoot,
  selectedTargetName,
  collapsedSections,
  sectionHeights,
  setSectionHeights,
  setCollapsedSections,
  containerRef,
  action,
}: UseSidebarEffectsProps) {
  const bomRequestIdRef = useRef(0);
  const variablesRequestIdRef = useRef(0);

  // Allow external UI actions (e.g., open/close sections)
  useEffect(() => {
    const handleUiAction = (event: Event) => {
      const detail = (event as CustomEvent).detail as {
        type?: 'openSection' | 'closeSection' | 'toggleSection';
        sectionId?: string;
      };
      if (!detail?.sectionId || !detail?.type) return;

      const sectionId = detail.sectionId as string;
      setCollapsedSections((prev) => {
        const next = new Set(prev);
        if (detail.type === 'openSection') {
          next.delete(sectionId);
        } else if (detail.type === 'closeSection') {
          next.add(sectionId);
        } else if (detail.type === 'toggleSection') {
          if (next.has(sectionId)) {
            next.delete(sectionId);
          } else {
            next.add(sectionId);
          }
        }
        return next;
      });
    };

    window.addEventListener('atopile:ui_action', handleUiAction);
    return () => window.removeEventListener('atopile:ui_action', handleUiAction);
  }, [setCollapsedSections]);

  // Initial data refresh after mount
  useEffect(() => {
    const timer = setTimeout(() => {
      action('refreshProblems');
      action('refreshPackages');
      action('refreshStdlib');
    }, 100);
    return () => clearTimeout(timer);
  }, [action]);

  // Fetch BOM data when project or target selection changes
  useEffect(() => {
    if (!selectedProjectRoot) {
      useStore.getState().setBomData(null);
      useStore.getState().setBomError(null);
      return;
    }

    if (!selectedTargetName) {
      return;
    }

    const requestId = ++bomRequestIdRef.current;
    useStore.getState().setLoadingBom(true);
    useStore.getState().setBomError(null);

    api.bom
      .get(selectedProjectRoot, selectedTargetName)
      .then((data) => {
        if (requestId !== bomRequestIdRef.current) return;
        useStore.getState().setBomData(data);
      })
      .catch((error) => {
        if (requestId !== bomRequestIdRef.current) return;
        const message = error instanceof Error ? error.message : 'Failed to load BOM';
        useStore.getState().setBomData(null);
        useStore.getState().setBomError(message);
      });
  }, [selectedProjectRoot, selectedTargetName]);

  // Fetch Variables data when project or target selection changes
  useEffect(() => {
    if (!selectedProjectRoot) {
      useStore.getState().setVariablesData(null);
      useStore.getState().setVariablesError(null);
      return;
    }

    if (!selectedTargetName) {
      return;
    }

    const requestId = ++variablesRequestIdRef.current;
    useStore.getState().setLoadingVariables(true);
    useStore.getState().setVariablesError(null);

    api.variables
      .get(selectedProjectRoot, selectedTargetName)
      .then((data) => {
        if (requestId !== variablesRequestIdRef.current) return;
        useStore.getState().setVariablesData(data);
      })
      .catch((error) => {
        if (requestId !== variablesRequestIdRef.current) return;
        const message = error instanceof Error ? error.message : 'Failed to load variables';
        useStore.getState().setVariablesData(null);
        useStore.getState().setVariablesError(message);
      });
  }, [selectedProjectRoot, selectedTargetName]);

  // Handle package install action results (only errors - success comes when packages refresh)
  // Also add a timeout fallback to clear stuck installing state
  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    const handleActionResult = (event: Event) => {
      const detail = (event as CustomEvent).detail as {
        action?: string;
        result?: {
          success?: boolean;
          error?: string;
        };
      };

      if (detail?.action === 'installPackage') {
        // Only handle errors - the install runs async in background
        // Success is detected when packages refresh and show as installed
        if (detail.result && !detail.result.success && detail.result.error) {
          // setInstallError already clears installingPackageId
          useStore.getState().setInstallError(detail.result.error);
          if (timeoutId) {
            clearTimeout(timeoutId);
            timeoutId = null;
          }
        } else if (detail.result?.success) {
          // Start a 60-second timeout as a fallback in case package refresh doesn't clear the state
          if (timeoutId) clearTimeout(timeoutId);
          timeoutId = setTimeout(() => {
            const currentInstalling = useStore.getState().installingPackageId;
            if (currentInstalling) {
              console.log('[install-debug] Timeout fallback: clearing stuck installingPackageId');
              useStore.getState().setInstallingPackage(null);
            }
          }, 60000);
        }
      }
    };
    window.addEventListener('atopile:action_result', handleActionResult);
    return () => {
      window.removeEventListener('atopile:action_result', handleActionResult);
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, []);

  // Subscribe to store changes to clear installing state when packages refresh
  // The backend only refreshes packages AFTER install completes, so any refresh
  // while we have installingPackageId means the install is done
  useEffect(() => {
    const unsubscribe = useStore.subscribe((state, prevState) => {
      const installingId = state.installingPackageId;
      if (!installingId) return;

      // If packages were updated while we have an installingPackageId, the install is complete
      // (The backend only calls refresh_packages_state after install finishes)
      if (state.packages !== prevState.packages && state.packages) {
        console.log('[install-debug] Packages refreshed while installing:', installingId);
        console.log('[install-debug] Clearing installingPackageId');
        useStore.getState().setInstallingPackage(null);
      }
    });
    return () => unsubscribe();
  }, []);

  // Auto-expand: detect unused space and cropped sections
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const sectionIds = ['projects', 'packages', 'problems', 'stdlib', 'variables', 'bom'];
    let debounceTimeoutId: ReturnType<typeof setTimeout> | null = null;

    const checkAutoExpand = () => {
      const containerHeight = container.clientHeight;
      let totalUsedHeight = 0;
      let croppedSectionInfo: { id: string; neededHeight: number; currentHeight: number } | null = null;

      for (const id of sectionIds) {
        if (collapsedSections.has(id)) continue;

        const section = container.querySelector(`[data-section-id="${id}"]`) as HTMLElement;
        if (!section) continue;

        const sectionBody = section.querySelector('.section-body') as HTMLElement;
        const titleBar = section.querySelector('.section-title-bar') as HTMLElement;

        if (titleBar) totalUsedHeight += titleBar.offsetHeight;
        if (sectionBody) {
          const currentBodyHeight = sectionBody.offsetHeight;
          const contentHeight = sectionBody.scrollHeight;
          totalUsedHeight += currentBodyHeight;

          const isOverflowing = contentHeight > currentBodyHeight + 5;

          if (isOverflowing && !croppedSectionInfo) {
            croppedSectionInfo = {
              id,
              neededHeight: contentHeight - currentBodyHeight,
              currentHeight: section.offsetHeight,
            };
          }
        }

        const resizeHandle = section.querySelector('.section-resize-handle') as HTMLElement;
        if (resizeHandle) totalUsedHeight += resizeHandle.offsetHeight;

        totalUsedHeight += 1;
      }

      const unusedSpace = containerHeight - totalUsedHeight;
      if (unusedSpace > 20 && croppedSectionInfo) {
        const expandAmount = Math.min(unusedSpace, croppedSectionInfo.neededHeight);
        const newHeight = croppedSectionInfo.currentHeight + expandAmount;

        const currentSetHeight = sectionHeights[croppedSectionInfo.id];
        if (!currentSetHeight || Math.abs(currentSetHeight - newHeight) > 5) {
          setSectionHeights(prev => ({
            ...prev,
            [croppedSectionInfo!.id]: newHeight,
          }));
        }
      }
    };

    const debouncedCheckAutoExpand = () => {
      if (debounceTimeoutId !== null) {
        clearTimeout(debounceTimeoutId);
      }
      debounceTimeoutId = setTimeout(checkAutoExpand, 100);
    };

    const initialTimeoutId = setTimeout(checkAutoExpand, 150);

    const resizeObserver = new ResizeObserver(debouncedCheckAutoExpand);
    resizeObserver.observe(container);

    return () => {
      clearTimeout(initialTimeoutId);
      if (debounceTimeoutId !== null) {
        clearTimeout(debounceTimeoutId);
      }
      resizeObserver.disconnect();
    };
  }, [collapsedSections, sectionHeights, setSectionHeights, containerRef]);
}
