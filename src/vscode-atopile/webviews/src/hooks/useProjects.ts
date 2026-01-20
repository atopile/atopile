/**
 * Hook for project-related state and actions.
 */

import { useCallback } from 'react';
import { useStore, useSelectedProject } from '../store';
import { api } from '../api/client';
import { sendAction } from '../api/websocket';

export function useProjects() {
  const projects = useStore((state) => state.projects);
  const selectedProjectRoot = useStore((state) => state.selectedProjectRoot);
  const selectedTargetNames = useStore((state) => state.selectedTargetNames);
  const expandedTargets = useStore((state) => state.expandedTargets);
  const isConnected = useStore((state) => state.isConnected);

  const selectedProject = useSelectedProject();

  const selectProject = useCallback((projectRoot: string | null) => {
    // Optimistic update
    useStore.getState().selectProject(projectRoot);
    // Notify backend
    sendAction('selectProject', { projectRoot });
  }, []);

  const toggleTarget = useCallback((targetName: string) => {
    // Optimistic update
    useStore.getState().toggleTarget(targetName);
    // Notify backend
    sendAction('toggleTarget', { targetName });
  }, []);

  const toggleTargetExpanded = useCallback((targetName: string) => {
    // Optimistic update (local-only state)
    useStore.getState().toggleTargetExpanded(targetName);
    // Notify backend
    sendAction('toggleTargetExpanded', { targetName });
  }, []);

  const refresh = useCallback(async () => {
    try {
      const response = await api.projects.list();
      useStore.getState().setProjects(response.projects);
    } catch (error) {
      console.error('Failed to refresh projects:', error);
    }
  }, []);

  return {
    projects,
    selectedProject,
    selectedProjectRoot,
    selectedTargetNames,
    expandedTargets,
    isConnected,
    selectProject,
    toggleTarget,
    toggleTargetExpanded,
    refresh,
  };
}
