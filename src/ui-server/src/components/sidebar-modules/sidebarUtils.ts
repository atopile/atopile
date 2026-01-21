/**
 * Sidebar utility functions and types.
 */

import type { Build, ModuleDefinition } from '../../types/build';

/**
 * Selection state for the sidebar tree.
 */
export interface Selection {
  type: 'none' | 'project' | 'build' | 'symbol';
  projectId?: string;
  buildId?: string;
  symbolId?: string;
  label?: string;
}

/**
 * Package info for the detail panel.
 */
export interface SelectedPackage {
  name: string;
  fullName: string;
  version?: string;
  description?: string;
  installed?: boolean;
  availableVersions?: { version: string; released: string }[];
  homepage?: string;
  repository?: string;
}

/**
 * Stage filter for problems panel.
 */
export interface StageFilter {
  stageName?: string;
  buildId?: string;
  projectId?: string;
}

/**
 * Default logo as PNG data URI (actual atopile logo).
 */
export const DEFAULT_LOGO = `data:image/png;base64,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`;

/**
 * Find a build for a specific target in a project.
 *
 * UNIFIED BUILD MATCHING: This function is the single source of truth for matching
 * builds to targets. Used by both projects and packages.
 *
 * Priority:
 * 1. Active builds (building/queued) matching by project_name + target
 * 2. Completed builds matching by name + project_name
 */
export function findBuildForTarget(
  builds: Build[] | undefined | null,
  projectName: string,
  targetName: string
): Build | undefined {
  // Safety check - builds might be undefined during initial load
  if (!builds || !Array.isArray(builds)) return undefined;

  // 1. Find active build (building/queued) for this specific target
  let build = builds.find(b => {
    if (b.status !== 'building' && b.status !== 'queued') return false;

    // Match by project (use projectName or derive from projectRoot)
    const buildProjectName = b.projectName || (b.projectRoot ? b.projectRoot.split('/').pop() : null);
    if (buildProjectName !== projectName) return false;

    // Match by target - use targets[] array (backend provides this)
    const targets = b.targets || [];
    if (targets.length > 0) {
      return targets.includes(targetName);
    }

    // If no targets specified (standalone build), match by name
    return b.name === targetName;
  });

  // 2. Fall back to any build (including completed) by name and project
  // This ensures completed builds show their final status and stages
  if (!build) {
    build = builds.find(b =>
      b.name === targetName &&
      (b.projectName === projectName || b.projectName === null)
    );
  }

  return build;
}

/**
 * Parse an entry point (e.g., "main.ato:App") into a symbol structure.
 * If modules are provided, they become children of the root symbol.
 */
export function parseEntryToSymbol(entry: string, modules?: ModuleDefinition[]) {
  if (!entry || !entry.includes(':')) return null;
  const [_file, moduleName] = entry.split(':');
  if (!moduleName) return null;

  // Build children from available modules (excluding the root entry itself)
  const children = (modules || [])
    .filter(m => m.entry !== entry)  // Exclude the root module
    .map(m => ({
      name: m.name,
      type: m.type as 'module' | 'interface' | 'component' | 'parameter',
      path: m.entry,
      children: [],  // Could be recursive in future
    }))
    .sort((a, b) => {
      // Sort by type first (modules, then components, then interfaces)
      const typeOrder = { module: 0, component: 1, interface: 2, parameter: 3 };
      const typeCompare = typeOrder[a.type] - typeOrder[b.type];
      if (typeCompare !== 0) return typeCompare;
      // Then by name
      return a.name.localeCompare(b.name);
    });

  return {
    name: moduleName,
    type: 'module' as const,
    path: entry,
    children,
  };
}
