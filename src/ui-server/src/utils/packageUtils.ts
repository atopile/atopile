/**
 * Shared utilities for package/version handling.
 * Used across ProjectCard, DependencyCard, and other components.
 */

/**
 * Format download count for display (e.g., 1234 -> "1.2k", 1500000 -> "1.5M")
 */
export function formatDownloads(count: number | null | undefined): string {
  if (count == null) return '0'
  if (count >= 1000000) {
    return (count / 1000000).toFixed(1).replace(/\.0$/, '') + 'M'
  }
  if (count >= 1000) {
    return (count / 1000).toFixed(1).replace(/\.0$/, '') + 'k'
  }
  return count.toString()
}

/**
 * Compare two semantic versions for sorting (descending order).
 * Returns negative if a > b, positive if a < b, 0 if equal.
 */
export function compareVersionsDesc(a: string, b: string): number {
  const aParts = a.split('.').map(part => parseInt(part, 10))
  const bParts = b.split('.').map(part => parseInt(part, 10))
  const maxLen = Math.max(aParts.length, bParts.length)
  for (let i = 0; i < maxLen; i += 1) {
    const aVal = Number.isFinite(aParts[i]) ? aParts[i] : 0
    const bVal = Number.isFinite(bParts[i]) ? bParts[i] : 0
    if (aVal !== bVal) return bVal - aVal
  }
  return b.localeCompare(a)
}

/**
 * Check if a version string is valid (not "unknown" or empty)
 */
export function isValidVersion(version: string | null | undefined): boolean {
  return !!version && version !== 'unknown'
}

/**
 * Filter and sort versions list
 */
export function normalizeVersions(versions: (string | null | undefined)[]): string[] {
  return versions
    .filter((v): v is string => isValidVersion(v))
    .sort(compareVersionsDesc)
}

/**
 * Parse a package identifier into publisher and name parts.
 * e.g., "atopile/resistors" -> { publisher: "atopile", name: "resistors" }
 */
export function parsePackageIdentifier(identifier: string): { publisher: string; name: string } {
  const parts = identifier.split('/')
  if (parts.length === 2) {
    return { publisher: parts[0], name: parts[1] }
  }
  return { publisher: 'unknown', name: identifier }
}

/**
 * Check if a package is installed in a specific project.
 */
export function isInstalledInProject(
  installedIn: string[] | undefined,
  targetProjectPath: string
): boolean {
  if (!installedIn || installedIn.length === 0) return false
  return installedIn.some(path =>
    path === targetProjectPath ||
    path.endsWith(`/${targetProjectPath}`) ||
    targetProjectPath.endsWith(path)
  )
}
