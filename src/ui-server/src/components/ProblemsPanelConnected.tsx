/**
 * ProblemsPanelConnected - Connected version using hooks.
 *
 * This component:
 * - Uses useProblems and useProjects hooks to get state
 * - Passes data to the presentational ProblemsPanel
 * - No props required - gets everything from store
 */

import { useCallback, useMemo } from 'react';
import { useProblems, useProjects } from '../hooks';
import { sendAction } from '../api/websocket';
import { ProblemsPanel } from './ProblemsPanel';
import type { Problem } from '../types/build';
import type { ProjectOption } from './ProjectDropdown';

export function ProblemsPanelConnected() {
  const { filteredProblems } = useProblems();
  const { projects, selectedProjectRoot } = useProjects();

  // Build a set of project names from discovered projects for fast lookup
  const discoveredProjectNames = useMemo(() => {
    return new Set(projects.map((p) => p.name));
  }, [projects]);

  // Filter problems:
  // 1. Only show problems from discovered projects (unless no projects discovered)
  // 2. If a specific project is selected, filter to just that project
  const projectFilteredProblems = useMemo(() => {
    let filtered = filteredProblems;

    // If we have discovered projects, only show problems from those projects
    if (projects.length > 0) {
      filtered = filtered.filter((p) => {
        // Include if problem's projectName matches a discovered project
        if (p.projectName && discoveredProjectNames.has(p.projectName)) return true;
        // Include if problem's file is within a discovered project root
        if (p.file) {
          return projects.some((proj) => p.file!.startsWith(proj.root));
        }
        return false;
      });
    }

    // If a specific project is selected, further filter to just that project
    if (selectedProjectRoot) {
      const selectedProject = projects.find((p) => p.root === selectedProjectRoot);
      if (selectedProject) {
        filtered = filtered.filter((p) => {
          // Match by project name
          if (p.projectName === selectedProject.name) return true;
          // Match by file path starting with project root
          if (p.file && p.file.startsWith(selectedProjectRoot)) return true;
          return false;
        });
      }
    }

    return filtered;
  }, [filteredProblems, selectedProjectRoot, projects, discoveredProjectNames]);

  // Transform problems to the format expected by ProblemsPanel
  const transformedProblems = projectFilteredProblems.map((p) => ({
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

  // Transform projects for the dropdown
  const transformedProjects: ProjectOption[] = projects.map((p) => ({
    id: p.root,
    name: p.name,
    root: p.root,
  }));

  const handleProblemClick = useCallback((problem: Problem) => {
    if (!problem.file) return;
    sendAction('openFile', {
      file: problem.file,
      line: problem.line,
      column: problem.column,
    });
  }, []);

  const handleSelectProject = useCallback((projectRoot: string | null) => {
    sendAction('selectProject', { projectRoot });
  }, []);

  return (
    <ProblemsPanel
      problems={transformedProblems}
      projects={transformedProjects}
      selectedProjectRoot={selectedProjectRoot}
      onSelectProject={handleSelectProject}
      onProblemClick={handleProblemClick}
    />
  );
}
