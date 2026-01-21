/**
 * ProblemsPanelConnected - Connected version using hooks.
 *
 * This component:
 * - Uses useProblems and useProjects hooks to get state
 * - Passes data to the presentational ProblemsPanel
 * - No props required - gets everything from store
 */

import { useCallback } from 'react';
import { useProblems, useProjects, useBuilds } from '../hooks';
import { useStore } from '../store';
import { ProblemsPanel } from './ProblemsPanel';
import type { Problem } from '../types/build';

// Type for selection used in BuildSelector
interface Selection {
  type: 'none' | 'project' | 'build' | 'symbol';
  projectId?: string;
  buildId?: string;
  symbolPath?: string;
  label?: string;
}

export function ProblemsPanelConnected() {
  const { filteredProblems, problemFilter } = useProblems();
  const { projects, selectedProjectRoot } = useProjects();
  const { builds, selectBuild } = useBuilds();
  const selectedBuildName = useStore((state) => state.selectedBuildName);

  // Build selection state for BuildSelector
  const selection: Selection = selectedBuildName
    ? { type: 'build', buildId: selectedBuildName, projectId: selectedProjectRoot || undefined }
    : selectedProjectRoot
    ? { type: 'project', projectId: selectedProjectRoot }
    : { type: 'none' };

  const handleSelectionChange = useCallback(
    (newSelection: Selection) => {
      if (newSelection.type === 'build' && newSelection.buildId) {
        selectBuild(newSelection.buildId);
      } else if (newSelection.type === 'project') {
        selectBuild(null);
      }
    },
    [selectBuild]
  );

  // Transform problems to the format expected by ProblemsPanel
  const transformedProblems = filteredProblems.map((p) => ({
    id: p.id,
    level: p.level,
    message: p.message,
    file: p.file,
    line: p.line,
    column: p.column,
    stage: p.stage,
    logger: p.logger,
    buildName: p.buildName,
    projectName: p.projectName,
    timestamp: p.timestamp,
    ato_traceback: p.atoTraceback,
  }));

  // Transform projects for BuildSelector
  const transformedProjects = projects.map((p) => ({
    id: p.root,
    name: p.name,
    type: 'project' as const,
    path: p.root,
    builds: p.targets.map((t) => ({
      id: t.name,
      name: t.name,
      entry: t.entry,
      status: t.lastBuild?.status || 'idle',
    })),
  }));

  const handleProblemClick = useCallback((problem: Problem) => {
    // Navigate to problem location
    // This would typically call a VS Code command to open the file
    console.log('Navigate to problem:', problem.file, problem.line);
  }, []);

  const handleToggleLevelFilter = useCallback((level: 'error' | 'warning') => {
    // Toggle level filter
    // For now, we just log - the store would need a toggleProblemLevelFilter action
    console.log('Toggle level filter:', level);
  }, []);

  return (
    <ProblemsPanel
      problems={transformedProblems}
      filter={problemFilter}
      selection={selection}
      onSelectionChange={handleSelectionChange}
      projects={transformedProjects}
      onProblemClick={handleProblemClick}
      onToggleLevelFilter={handleToggleLevelFilter}
    />
  );
}
