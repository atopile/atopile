/**
 * Sidebar Effects Hook
 * Handles all useEffect logic for the Sidebar component
 */

import { useEffect, useRef } from 'react';
import { useStore } from '../../store';
import { api } from '../../api/client';
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
  action: (name: string, data?: Record<string, unknown>) => void;
}

export function useSidebarEffects({
  selectedProjectRoot,
  selectedTargetName,
  panels,
  action,
}: UseSidebarEffectsProps) {
  const bomRequestIdRef = useRef(0);
  const variablesRequestIdRef = useRef(0);

  const fetchPackages = async () => {
    const store = useStore.getState();
    store.setLoadingPackages(true);
    try {
      const response = await api.packages.list();
      store.setPackages(response.packages || []);
    } catch (error) {
      console.warn('[UI] Failed to fetch packages', error);
      store.setPackages([]);
    }
  };

  const fetchStdlib = async () => {
    const store = useStore.getState();
    store.setLoadingStdlib(true);
    try {
      const response = await api.stdlib.list();
      store.setStdlibItems(response.items || []);
    } catch (error) {
      console.warn('[UI] Failed to fetch stdlib', error);
      store.setStdlibItems([]);
    }
  };

  const fetchProblems = async () => {
    const store = useStore.getState();
    store.setLoadingProblems(true);
    try {
      const response = await api.problems.list();
      store.setProblems(response.problems || []);
    } catch (error) {
      console.warn('[UI] Failed to fetch problems', error);
      store.setProblems([]);
    }
  };

  const fetchDependencies = async (projectRoot: string) => {
    const store = useStore.getState();
    try {
      const response = await api.dependencies.list(projectRoot);
      store.setProjectDependencies(projectRoot, response.dependencies || []);
    } catch (error) {
      console.warn('[UI] Failed to fetch dependencies', error);
      store.setProjectDependencies(projectRoot, []);
    }
  };

  const fetchBom = async (projectRoot: string, targetName: string) => {
    const store = useStore.getState();
    store.setLoadingBom(true);
    store.setBomError(null);
    try {
      const response = await api.bom.get(projectRoot, targetName);
      store.setBomData(response || null);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch BOM';
      console.warn('[UI] Failed to fetch BOM', error);
      store.setBomError(message);
    }
  };

  const fetchVariables = async (projectRoot: string, targetName: string) => {
    const store = useStore.getState();
    store.setLoadingVariables(true);
    store.setVariablesError(null);
    try {
      const response = await api.variables.get(projectRoot, targetName);
      store.setVariablesData(response || null);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch variables';
      console.warn('[UI] Failed to fetch variables', error);
      store.setVariablesError(message);
    }
  };

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
      void fetchProblems();
      void fetchPackages();
      void fetchStdlib();
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
    void fetchBom(selectedProjectRoot, selectedTargetName);
  }, [selectedProjectRoot, selectedTargetName]);

  // Fetch dependencies for active project (packages panel)
  useEffect(() => {
    if (!selectedProjectRoot) return;
    const deps = useStore.getState().projectDependencies?.[selectedProjectRoot];
    if (deps !== undefined) return;
    void fetchDependencies(selectedProjectRoot);
  }, [selectedProjectRoot, action]);

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
    void fetchVariables(selectedProjectRoot, selectedTargetName);
  }, [selectedProjectRoot, selectedTargetName]);

  // Package install state is owned by backend; frontend is read-only.
  // Auto-expand/collapse is now handled by usePanelSizing hook based on store state.
}
