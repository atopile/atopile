/**
 * Sidebar utility functions and types.
 */

import type { Build, ModuleDefinition } from '../../types/build';

/**
 * Smart truncation for two strings that need to fit in a limited space.
 * Trims from the longest string first, equalizing lengths when both need trimming.
 *
 * Example with maxTotal=100:
 * - (55, 70) -> (50, 50) - both trimmed to equal length
 * - (25, 60) -> (25, 60) - both fit, no change
 * - (25, 90) -> (25, 72) - only longer one trimmed (with ellipsis)
 *
 * @param str1 First string
 * @param str2 Second string
 * @param maxTotal Maximum total characters allowed for both strings
 * @param ellipsis String to append when truncating (default: '…')
 * @returns Tuple of [truncated str1, truncated str2]
 */
export function smartTruncatePair(
  str1: string,
  str2: string,
  maxTotal: number,
  ellipsis: string = '…'
): [string, string] {
  const len1 = str1.length;
  const len2 = str2.length;
  const totalLen = len1 + len2;

  // If both fit, return unchanged
  if (totalLen <= maxTotal) {
    return [str1, str2];
  }

  const ellipsisLen = ellipsis.length;

  // Calculate how much each string can be at most
  // We want to equalize lengths when both are long
  const halfMax = Math.floor(maxTotal / 2);

  let result1 = str1;
  let result2 = str2;

  if (len1 <= halfMax && len2 > maxTotal - len1) {
    // str1 fits in its half, only trim str2
    const maxLen2 = maxTotal - len1;
    if (maxLen2 > ellipsisLen) {
      result2 = str2.slice(0, maxLen2 - ellipsisLen) + ellipsis;
    } else {
      result2 = ellipsis.slice(0, maxLen2);
    }
  } else if (len2 <= halfMax && len1 > maxTotal - len2) {
    // str2 fits in its half, only trim str1
    const maxLen1 = maxTotal - len2;
    if (maxLen1 > ellipsisLen) {
      result1 = str1.slice(0, maxLen1 - ellipsisLen) + ellipsis;
    } else {
      result1 = ellipsis.slice(0, maxLen1);
    }
  } else {
    // Both need trimming - equalize to half each
    const targetLen = halfMax - ellipsisLen;
    if (targetLen > 0) {
      if (len1 > halfMax) {
        result1 = str1.slice(0, targetLen) + ellipsis;
      }
      if (len2 > halfMax) {
        result2 = str2.slice(0, targetLen) + ellipsis;
      }
    } else {
      // Very small maxTotal - just show ellipsis
      result1 = ellipsis.slice(0, halfMax);
      result2 = ellipsis.slice(0, halfMax);
    }
  }

  return [result1, result2];
}

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
  latestVersion?: string;
  description?: string;
  installed?: boolean;
  availableVersions?: { version: string; released: string }[];
  homepage?: string;
  repository?: string;
}

export interface SelectedPart {
  lcsc: string;
  mpn: string;
  manufacturer: string;
  description?: string;
  package?: string;
  datasheet_url?: string;
  image_url?: string;
  installed?: boolean;
}

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

    // Match by target (backend provides single target per build)
    if (b.target) {
      return b.target === targetName;
    }

    // If no target specified (standalone build), match by name
    return b.name === targetName;
  });

  // 2. Fallback: find by name, but only if it's an active build
  // Don't use completed builds here - they should come from lastBuild instead
  if (!build) {
    build = builds.find(b =>
      (b.status === 'building' || b.status === 'queued') &&
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
