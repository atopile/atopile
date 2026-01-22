/**
 * Custom hook for sidebar data transformations.
 */

import { useMemo } from 'react';
import type { QueuedBuild } from '../BuildQueuePanel';
import { type Selection, type StageFilter } from './sidebarUtils';

// Local helper functions that work with any build structure
function findBuildForTarget(
  builds: any[] | undefined | null,
  projectName: string,
  targetName: string,
  projectRoot?: string
): any | undefined {
  if (!builds || !Array.isArray(builds)) return undefined;

  let build = builds.find(b => {
    if (b.status !== 'building' && b.status !== 'queued') return false;
    if (projectRoot && b.projectRoot && b.projectRoot === projectRoot) {
      return true;
    }
    const buildProjectName = b.projectName || (b.projectRoot ? b.projectRoot.split('/').pop() : null);
    if (buildProjectName !== projectName) return false;
    const targets = b.targets || [];
    if (targets.length > 0) {
      return targets.includes(targetName);
    }
    return b.name === targetName;
  });

  // Fallback: find by name, but only if it's an active build
  if (!build) {
    build = builds.find(b =>
      (b.status === 'building' || b.status === 'queued') &&
      b.name === targetName &&
      (b.projectName === projectName || b.projectName === null) &&
      (!projectRoot || !b.projectRoot || b.projectRoot === projectRoot)
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

// Normalize lastBuild status - treat "interrupted", "building", "queued" as "idle"
// since they indicate stale state from a previous session
function normalizeLastBuildStatus(status: string | undefined): string {
  if (!status) return 'idle';
  if (status === 'failed') return 'error';
  if (status === 'interrupted' || status === 'building' || status === 'queued') return 'idle';
  return status;
}

type SidebarState = any;

interface UseSidebarDataParams {
  state: SidebarState | null;
  selection: Selection;
  activeStageFilter: StageFilter | null;
}

export function useSidebarData({ state, selection, activeStageFilter }: UseSidebarDataParams) {
  // Transform state projects - KEEP: expensive nested map operations
  const transformedProjects = useMemo((): any[] => {
    if (!state?.projects?.length) return [];

    const activeBuilds = [
      ...(state?.queuedBuilds || []),
      ...(state?.builds || []),
    ];

    return state.projects.map((p: any) => {
      const projectModules = state.projectModules?.[p.root] || [];

      const builds = p.targets.map((t: any) => {
        const build = findBuildForTarget(activeBuilds, p.name, t.name, p.root);
        const rootSymbol = parseEntryToSymbol(t.entry, projectModules);
        const activeStages = build?.stages && build.stages.length > 0 ? build.stages : null;
        const historicalStages = t.lastBuild?.stages;
        const displayStages = activeStages || historicalStages || [];

        return {
          id: t.name,
          name: t.name,
          entry: t.entry,
          status: build?.status === 'failed' ? 'error' : (build?.status || normalizeLastBuildStatus(t.lastBuild?.status)),
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
            status: normalizeLastBuildStatus(t.lastBuild.status),
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

        if (timestamp && (!mostRecentTimestamp || timestamp > mostRecentTimestamp)) {
          mostRecentTimestamp = timestamp;
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
  }, [state?.projects, state?.builds, state?.projectModules]);

  // Transform state packages - KEEP: expensive filter/map operations
  const transformedPackages = useMemo((): any[] => {
    if (!state?.packages?.length) return [];

    const activeBuilds = [
      ...(state?.queuedBuilds || []),
      ...(state?.builds || []),
    ];

    return state.packages
      .filter((pkg: any) => pkg && pkg.identifier && pkg.name)
      .map((pkg: any) => {
        const targetNames = ['default', 'usage'];

        const packageBuilds = targetNames.map(targetName => {
          const build = findBuildForTarget(activeBuilds, pkg.name, targetName);

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

          if (timestamp && (!mostRecentTimestamp || timestamp > mostRecentTimestamp)) {
            mostRecentTimestamp = timestamp;
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

  // Combine projects and packages - NO MEMO: trivial concat
  const projects = [...transformedProjects, ...transformedPackages];

  // Count projects/packages - NO MEMO: trivial loop
  let projectCount = 0;
  let packageCount = 0;
  for (const p of projects) {
    if (p.type === 'package') packageCount++;
    else projectCount++;
  }

  // Queued builds - NO MEMO: just property access with default
  const queuedBuilds: QueuedBuild[] = (state?.queuedBuilds || []) as QueuedBuild[];

  // Index projects by ID - KEEP: creates Map for O(1) lookups used in filtering
  const projectsById = useMemo(() => {
    return new Map(projects.map(p => [p.id, p]));
  }, [projects]);

  // Problems - NO MEMO: just property access with default
  const problems = state?.problems || [];

  // Filtered problems - KEEP: complex filtering logic
  const filteredProblems = useMemo(() => {
    const filter = state?.problemFilter;

    const normalizeStage = (name: string): string => {
      return name.toLowerCase().replace(/[-_\s]+/g, '');
    };

    const stageMatches = (filterStage: string, problemStage: string): boolean => {
      if (filterStage === problemStage) return true;
      const normFilter = normalizeStage(filterStage);
      const normProblem = normalizeStage(problemStage);
      if (normFilter === normProblem) return true;
      if (normFilter.includes(normProblem) || normProblem.includes(normFilter)) return true;
      return false;
    };

    return problems.filter((p: any) => {
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
  }, [problems, state?.problemFilter, activeStageFilter, selection, projectsById]);

  // Count errors/warnings - NO MEMO: trivial loop
  let totalErrors = 0;
  let totalWarnings = 0;
  for (const p of filteredProblems) {
    if (p.level === 'error') totalErrors++;
    else if (p.level === 'warning') totalWarnings++;
  }

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
