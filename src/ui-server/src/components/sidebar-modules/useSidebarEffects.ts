/**
 * Sidebar Effects Hook
 * Handles all useEffect logic for the Sidebar component
 */

import { useEffect, useRef } from 'react';
import { useStore } from '../../store';
import { api } from '../../api/client';
import { fetchInitialData } from '../../api/eventHandler';
import type { PanelId } from '../../utils/panelConfig';

interface PanelControls {
  expandPanel: (id: PanelId) => void;
  collapsePanel: (id: PanelId) => void;
  togglePanel: (id: PanelId) => void;
}

interface UseSidebarEffectsProps {
  selectedProjectRoot: string | null;
  selectedTargetName: string | null;
  panels: PanelControls;
}

export function useSidebarEffects({
  selectedProjectRoot,
  selectedTargetName,
  panels,
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

      const sectionId = detail.sectionId as PanelId;
      if (detail.type === 'openSection') {
        panels.expandPanel(sectionId);
      } else if (detail.type === 'closeSection') {
        panels.collapsePanel(sectionId);
      } else if (detail.type === 'toggleSection') {
        panels.togglePanel(sectionId);
      }
    };

    window.addEventListener('atopile:ui_action', handleUiAction);
    return () => window.removeEventListener('atopile:ui_action', handleUiAction);
  }, [panels]);

  // Initial data refresh after mount
  useEffect(() => {
    const timer = setTimeout(() => {
      void fetchInitialData();
    }, 100);
    return () => clearTimeout(timer);
  }, []);

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
      .then((result) => {
        if (requestId !== bomRequestIdRef.current) return;
        useStore.getState().setBomData(result);
      })
      .catch((error) => {
        if (requestId !== bomRequestIdRef.current) return;
        useStore.getState().setBomError(
          error instanceof Error ? error.message : String(error)
        );
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
      .then((result) => {
        if (requestId !== variablesRequestIdRef.current) return;
        useStore.getState().setVariablesData(result);
      })
      .catch((error) => {
        if (requestId !== variablesRequestIdRef.current) return;
        useStore.getState().setVariablesError(
          error instanceof Error ? error.message : String(error)
        );
      });
  }, [selectedProjectRoot, selectedTargetName]);

  // Auto-expand/collapse is now handled by usePanelSizing hook based on store state.
}
