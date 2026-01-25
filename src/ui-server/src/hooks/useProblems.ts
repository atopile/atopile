/**
 * Hook for problems/diagnostics state and actions.
 */

import { useCallback } from 'react';
import { useStore, useFilteredProblems } from '../store';
import { api } from '../api/client';

export function useProblems() {
  const problems = useStore((state) => state.problems);
  const isLoadingProblems = useStore((state) => state.isLoadingProblems);
  const problemFilter = useStore((state) => state.problemFilter);

  const filteredProblems = useFilteredProblems();

  const refresh = useCallback(async (_options?: { projectRoot?: string; buildName?: string; level?: string }) => {
    const store = useStore.getState();
    store.setLoadingProblems(true);
    try {
      const result = await api.problems.list({
        developerMode: store.developerMode,
      });
      store.setProblems(result.problems);
    } catch (error) {
      console.error('Failed to fetch problems:', error);
      store.setLoadingProblems(false);
    }
  }, []);

  // Counts by level
  const errorCount = problems.filter((p) => p.level === 'error').length;
  const warningCount = problems.filter((p) => p.level === 'warning').length;

  // Filtered counts
  const filteredErrorCount = filteredProblems.filter(
    (p) => p.level === 'error'
  ).length;
  const filteredWarningCount = filteredProblems.filter(
    (p) => p.level === 'warning'
  ).length;

  return {
    problems,
    filteredProblems,
    isLoadingProblems,
    problemFilter,
    errorCount,
    warningCount,
    filteredErrorCount,
    filteredWarningCount,
    refresh,
  };
}
