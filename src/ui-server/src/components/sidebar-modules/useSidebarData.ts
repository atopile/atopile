/**
 * Custom hook for sidebar data transformations.
 * Contains all memoized computations for transforming state data.
 */

import { useMemo } from 'react';
import type { QueuedBuild } from '../BuildQueuePanel';
import { logPerf } from '../../perf';
import { type Selection, type StageFilter } from './sidebarUtils';

// Local helper functions that work with any build structure
function findBuildForTarget(
  builds: any[] | undefined | null,
  projectName: string,
  targetName: string
): any | undefined {
  if (!builds || !Array.isArray(builds)) return undefined;

  let build = builds.find(b => {
    if (b.status !== 'building' && b.status !== 'queued') return false;
    const buildProjectName = b.projectName || (b.projectRoot ? b.projectRoot.split('/').pop() : null);
    if (buildProjectName !== projectName) return false;
    const targets = b.targets || [];
    if (targets.length > 0) {
      return targets.includes(targetName);
    }
    return b.name === targetName;
  });

  if (!build) {
    build = builds.find(b =>
      b.name === targetName &&
      (b.projectName === projectName || b.projectName === null)
    );
  }

  return build;
}

function parseEntryToSymbol(entry: string, modules?: any[]) {
  if (!entry || !entry.includes(':')) return null;
  const [_file, moduleName] = entry.split(':');
  if (!moduleName) return null;

  const children = (modules || [])
    .filter(m => m.entry !== entry)
    .map(m => ({
      name: m.name,
      type: m.type as 'module' | 'interface' | 'component' | 'parameter',
      path: m.entry,
      children: [],
    }))
    .sort((a, b) => {
      const typeOrder: Record<string, number> = { module: 0, component: 1, interface: 2, parameter: 3 };
      const typeCompare = (typeOrder[a.type] || 99) - (typeOrder[b.type] || 99);
      if (typeCompare !== 0) return typeCompare;
      return a.name.localeCompare(b.name);
    });

  return {
    name: moduleName,
    type: 'module' as const,
    path: entry,
    children,
  };
}

// Use a generic state type to avoid strict type mismatches with the store
// The actual properties are accessed dynamically
type SidebarState = any;

interface UseSidebarDataParams {
  state: SidebarState | null;
  selection: Selection;
  activeStageFilter: StageFilter | null;
}

export function useSidebarData({ state, selection, activeStageFilter }: UseSidebarDataParams) {
  // Transform state projects to the format our components expect
  const transformedProjects = useMemo((): any[] => {
    const start = performance.now();
    if (!state?.projects?.length) return [];

    const result = state.projects.map((p: any) => {
      // Get available modules for this project (for tree view)
      const projectModules = state.projectModules?.[p.root] || [];

      // Transform builds/targets with lastBuild info
      const builds = p.targets.map((t: any) => {
        // UNIFIED: Use shared findBuildForTarget helper
        const build = findBuildForTarget(state.builds, p.name, t.name);
        const rootSymbol = parseEntryToSymbol(t.entry, projectModules);
        // Get stages from active build or fall back to lastBuild
        const activeStages = build?.stages && build.stages.length > 0 ? build.stages : null;
        const historicalStages = t.lastBuild?.stages;
        const displayStages = activeStages || historicalStages || [];

        return {
          id: t.name,
          name: t.name,
          entry: t.entry,
          status: build?.status === 'failed' ? 'error' : (build?.status || (t.lastBuild?.status === 'failed' ? 'error' : (t.lastBuild?.status || 'idle'))),
          warnings: build?.warnings ?? t.lastBuild?.warnings,
          errors: build?.errors ?? t.lastBuild?.errors,
          elapsedSeconds: build?.elapsedSeconds,
          duration: t.lastBuild?.elapsedSeconds,
          buildId: build?.buildId,
          stages: displayStages.map((s: any) => ({
            ...s,
            status: s.status === 'failed' ? 'error' : s.status,
          })),
          symbols: rootSymbol ? [rootSymbol] : [],
          queuePosition: build?.queuePosition,
          lastBuild: t.lastBuild ? {
            status: t.lastBuild.status === 'failed' ? 'error' : t.lastBuild.status,
            timestamp: t.lastBuild.timestamp,
            elapsedSeconds: t.lastBuild.elapsedSeconds,
            warnings: t.lastBuild.warnings,
            errors: t.lastBuild.errors,
            stages: t.lastBuild.stages?.map((s: any) => ({
              name: s.name,
              displayName: s.displayName,
              status: s.status === 'failed' ? 'error' : s.status,
              elapsedSeconds: s.elapsedSeconds,
            })),
          } : undefined,
        };
      });

      // Calculate project-level status from targets
      let projectStatus: 'success' | 'warning' | 'failed' | 'error' | undefined;
      let mostRecentTimestamp: string | undefined;

      for (const build of builds) {
        const status = build.status !== 'idle' ? build.status : build.lastBuild?.status;
        const timestamp = build.lastBuild?.timestamp;

        if (status === 'error' || status === 'failed') {
          projectStatus = 'error';
        } else if (status === 'warning' && projectStatus !== 'error') {
          projectStatus = 'warning';
        } else if (status === 'success' && !projectStatus) {
          projectStatus = 'success';
        }

        if (timestamp) {
          if (!mostRecentTimestamp || timestamp > mostRecentTimestamp) {
            mostRecentTimestamp = timestamp;
          }
        }
      }

      return {
        id: p.root,
        name: p.name,
        type: 'project' as const,
        root: p.root,
        builds,
        lastBuildStatus: projectStatus,
        lastBuildTimestamp: mostRecentTimestamp,
      };
    });
    logPerf('sidebar:transform-projects', performance.now() - start, {
      projects: result.length,
      builds: state.builds?.length ?? 0,
    });
    return result;
  }, [state?.projects, state?.builds, state?.projectModules]);

  // Transform state packages to the format that ProjectsPanel expects
  const transformedPackages = useMemo((): any[] => {
    if (!state?.packages?.length) return [];

    return state.packages
      .filter((pkg: any) => pkg && pkg.identifier && pkg.name)
      .map((pkg: any) => {
        // Standard target names for packages
        const targetNames = ['default', 'usage'];

        // Look up builds for this package using the unified helper
        const packageBuilds = targetNames.map(targetName => {
          const build = findBuildForTarget(state.builds, pkg.name, targetName);

          return {
            id: targetName,
            name: targetName,
            entry: `${pkg.name || 'unknown'}.ato:${(pkg.name || 'unknown').replace(/-/g, '_')}`,
            status: build?.status || 'idle',
            buildId: build?.buildId,
            elapsedSeconds: build?.elapsedSeconds,
            warnings: build?.warnings,
            errors: build?.errors,
            stages: build?.stages || [],
            queuePosition: build?.queuePosition,
            lastBuild: (build && (build.status === 'success' || build.status === 'failed' || build.status === 'warning') && build.startedAt) ? {
              status: build.status === 'failed' ? 'error' : build.status,
              timestamp: new Date((build.startedAt + (build.elapsedSeconds || 0)) * 1000).toISOString(),
              elapsedSeconds: build.elapsedSeconds,
              warnings: build.warnings || 0,
              errors: build.errors || 0,
            } : undefined,
          };
        });

        // Calculate package-level last build status
        let packageStatus: 'success' | 'warning' | 'failed' | 'error' | undefined;
        let mostRecentTimestamp: string | undefined;

        for (const build of packageBuilds) {
          const status = build.status !== 'idle' ? build.status : build.lastBuild?.status;
          const timestamp = build.lastBuild?.timestamp;

          if (status === 'error' || status === 'failed') {
            packageStatus = 'error';
          } else if (status === 'warning' && packageStatus !== 'error') {
            packageStatus = 'warning';
          } else if (status === 'success' && !packageStatus) {
            packageStatus = 'success';
          }

          if (timestamp) {
            if (!mostRecentTimestamp || timestamp > mostRecentTimestamp) {
              mostRecentTimestamp = timestamp;
            }
          }
        }

        return {
          id: pkg.identifier,
          name: pkg.name,
          type: 'package' as const,
          path: `packages/${pkg.identifier}`,
          version: pkg.version || undefined,
          latestVersion: pkg.latestVersion,
          installed: pkg.installed ?? false,
          installedIn: pkg.installedIn || [],
          publisher: pkg.publisher || undefined,
          summary: pkg.summary || pkg.description || '',
          description: pkg.description || pkg.summary || '',
          homepage: pkg.homepage,
          repository: pkg.repository,
          license: pkg.license,
          keywords: pkg.keywords || [],
          downloads: pkg.downloads,
          versionCount: pkg.versionCount,
          builds: packageBuilds,
          lastBuildStatus: packageStatus,
          lastBuildTimestamp: mostRecentTimestamp,
        };
      });
  }, [state?.packages, state?.builds]);

  // Combine projects and packages
  const projects = useMemo((): any[] => {
    return [...transformedProjects, ...transformedPackages];
  }, [transformedProjects, transformedPackages]);

  // Memoize project/package counts
  const { projectCount, packageCount } = useMemo(() => {
    let projCount = 0;
    let pkgCount = 0;
    for (const p of projects) {
      if (p.type === 'package') pkgCount++;
      else projCount++;
    }
    return { projectCount: projCount, packageCount: pkgCount };
  }, [projects]);

  // Queued builds from state
  const queuedBuilds = useMemo((): QueuedBuild[] => {
    return (state?.queuedBuilds || []) as QueuedBuild[];
  }, [state?.queuedBuilds]);

  // Pre-index projects by ID for O(1) lookup during filtering
  const projectsById = useMemo(() => {
    return new Map(projects.map(p => [p.id, p]));
  }, [projects]);

  // Problems from state
  const problems = useMemo(() => {
    return state?.problems || [];
  }, [state?.problems]);

  // Memoized filtered problems with optimized lookups
  const filteredProblems = useMemo(() => {
    const start = performance.now();
    const filter = state?.problemFilter;

    // Helper to normalize stage names for comparison
    const normalizeStage = (name: string): string => {
      return name.toLowerCase().replace(/[-_\s]+/g, '');
    };

    // Check if two stage names match (flexible matching)
    const stageMatches = (filterStage: string, problemStage: string): boolean => {
      if (filterStage === problemStage) return true;
      const normFilter = normalizeStage(filterStage);
      const normProblem = normalizeStage(problemStage);
      if (normFilter === normProblem) return true;
      if (normFilter.includes(normProblem) || normProblem.includes(normFilter)) return true;
      return false;
    };

    const result = problems.filter((p: any) => {
      // Filter by active stage filter (from clicking on a stage/build)
      if (activeStageFilter) {
        if (activeStageFilter.stageName) {
          if (!p.stage) return false;
          if (!stageMatches(activeStageFilter.stageName, p.stage)) return false;
        }
        if (activeStageFilter.buildId && p.buildName) {
          if (p.buildName !== activeStageFilter.buildId) return false;
        }
        if (activeStageFilter.projectId && p.projectName) {
          const selectedProject = projectsById.get(activeStageFilter.projectId);
          if (selectedProject && p.projectName !== selectedProject.name) {
            return false;
          }
        }
        return true;
      }

      // Filter by selection (project/build) when no stage filter
      if (selection.type === 'project' && selection.projectId) {
        const selectedProject = projectsById.get(selection.projectId);
        if (selectedProject && p.projectName && p.projectName !== selectedProject.name) {
          return false;
        }
      } else if (selection.type === 'build' && selection.projectId && selection.buildId) {
        const selectedProject = projectsById.get(selection.projectId);
        if (selectedProject && p.projectName && p.projectName !== selectedProject.name) {
          return false;
        }
        if (p.buildName && p.buildName !== selection.buildId) {
          return false;
        }
      }

      if (!filter) return true;
      if (filter.levels && filter.levels.length > 0 && !filter.levels.includes(p.level)) return false;
      if (filter.buildNames && filter.buildNames.length > 0 && p.buildName && !filter.buildNames.includes(p.buildName)) return false;
      if (filter.stageIds && filter.stageIds.length > 0 && p.stage && !filter.stageIds.includes(p.stage)) return false;
      return true;
    });
    logPerf('sidebar:filter-problems', performance.now() - start, {
      total: problems.length,
      filtered: result.length,
    });
    return result;
  }, [problems, state?.problemFilter, activeStageFilter, selection, projectsById]);

  // Combined error/warning count in single pass
  const { totalErrors, totalWarnings } = useMemo(() => {
    let errors = 0;
    let warnings = 0;
    for (const p of filteredProblems) {
      if (p.level === 'error') errors++;
      else if (p.level === 'warning') warnings++;
    }
    return { totalErrors: errors, totalWarnings: warnings };
  }, [filteredProblems]);

  return {
    projects,
    projectCount,
    packageCount,
    queuedBuilds,
    projectsById,
    problems,
    filteredProblems,
    totalErrors,
    totalWarnings,
  };
}
