/**
 * Custom hook for sidebar data transformations.
 */

import { useMemo } from 'react';
import type { QueuedBuild } from '../../types/build';

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
    // Check if build target matches
    if (b.target) {
      return b.target === targetName;
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
}

export function useSidebarData({ state }: UseSidebarDataParams) {
  // Transform state projects - KEEP: expensive nested map operations
  const transformedProjects = useMemo((): any[] => {
    if (!state?.projects?.length) return [];

    const activeBuilds = (state?.builds || []).filter((b: any) =>
      b.status === 'queued' || b.status === 'building'
    );

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
            buildId: t.lastBuild.buildId,
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
            lastBuild: (build && (build.status === 'success' || build.status === 'failed' || build.status === 'warning') && build.startedAt && typeof build.elapsedSeconds === 'number') ? {
              status: build.status === 'failed' ? 'error' : build.status,
              timestamp: new Date((build.startedAt + build.elapsedSeconds) * 1000).toISOString(),
              elapsedSeconds: build.elapsedSeconds,
              warnings: build.warnings || 0,
              errors: build.errors || 0,
              buildId: build.buildId,
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

  // Queued builds + recent completed builds for display in Build Queue
  // Combines active builds with recently completed ones for quick review
  const queuedBuilds = useMemo((): QueuedBuild[] => {
    return (state?.queuedBuilds || []) as QueuedBuild[];
  }, [state?.queuedBuilds]);

  return {
    projects,
    projectCount,
    packageCount,
    queuedBuilds,
  };
}
