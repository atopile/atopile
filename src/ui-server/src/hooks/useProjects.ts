/**
 * Hook for project-related state and actions.
 */

import { useCallback } from 'react';
import { useStore, useSelectedProject } from '../store';
import { sendAction } from '../api/websocket';

export function useProjects() {
  const projects = useStore((state) => state.projects);
  const selectedProjectRoot = useStore((state) => state.selectedProjectRoot);
  const selectedTargetNames = useStore((state) => state.selectedTargetNames);
  const expandedTargets = useStore((state) => state.expandedTargets);
  const isConnected = useStore((state) => state.isConnected);

  const selectedProject = useSelectedProject();

  const selectProject = useCallback((projectRoot: string | null) => {
    useStore.getState().selectProject(projectRoot);
  }, []);

  const toggleTarget = useCallback((targetName: string) => {
    useStore.getState().toggleTarget(targetName);
  }, []);

  const toggleTargetExpanded = useCallback((targetName: string) => {
    useStore.getState().toggleTargetExpanded(targetName);
  }, []);

  const refresh = useCallback(async () => {
    sendAction('refreshProjects');
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
