/** Normalize a file path: convert backslashes to forward slashes and strip trailing slashes (preserving bare "/"). */
export function normalizePath(path: string): string {
  const normalized = path.replace(/\\/g, "/");
  return normalized.length > 1 ? normalized.replace(/\/+$/, "") : normalized;
}

/** Return the last two segments of a path for compact display. */
export function formatPath(path: string): string {
  if (!path) return "";
  const parts = path.split("/");
  return parts.slice(-2).join("/");
}

/** Join a base path with a relative path, stripping trailing slashes from the base. */
export function joinPath(base: string, relativePath: string): string {
  return `${base.replace(/[\\/]+$/, "")}/${relativePath}`;
}

/** Return the portion of `fullPath` relative to `projectRoot`, or null if not under it. */
export function relativeToProject(projectRoot: string, fullPath: string): string | null {
  const root = normalizePath(projectRoot);
  const absolute = normalizePath(fullPath);
  if (absolute === root) {
    return "";
  }
  if (!absolute.startsWith(`${root}/`)) {
    return null;
  }
  return absolute.slice(root.length + 1);
}

/** Return the parent directory of a relative path, or "" if at the root level. */
export function parentRelativePath(relativePath: string): string {
  const index = relativePath.lastIndexOf("/");
  return index === -1 ? "" : relativePath.slice(0, index);
}

/** Return the last segment (file or directory name) of a path. */
export function basename(filePath: string): string {
  const normalized = normalizePath(filePath);
  const index = normalized.lastIndexOf("/");
  return index === -1 ? normalized : normalized.slice(index + 1);
}

/** Join a directory path with a child name, trimming whitespace from the name. */
export function joinChildPath(directoryPath: string, name: string): string {
  return joinPath(directoryPath, name.trim());
}

/** Validate a file/folder name. Returns an error message or null if valid. */
export function validateName(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return "Name cannot be empty.";
  }
  if (trimmed.includes("/") || trimmed.includes("\\")) {
    return "Name cannot contain path separators.";
  }
  return null;
}

/** Return all ancestor directory paths for a relative path (excluding the path itself). */
export function ancestorPaths(relativePath: string): string[] {
  const segments = relativePath.split("/").filter(Boolean);
  return segments.slice(0, -1).map((_, index) => segments.slice(0, index + 1).join("/"));
}

/** Return the target root relative to the project root, or null when they match. */
export function relativeTargetRoot(projectRoot: string, targetRoot: string): string | null {
  const normalizedProjectRoot = normalizePath(projectRoot);
  const normalizedTargetRoot = normalizePath(targetRoot);
  if (normalizedProjectRoot === normalizedTargetRoot) {
    return null;
  }
  const prefix = `${normalizedProjectRoot}/`;
  if (normalizedTargetRoot.startsWith(prefix)) {
    return normalizedTargetRoot.slice(prefix.length);
  }
  return formatPath(normalizedTargetRoot);
}
