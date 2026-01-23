/**
 * Shared types for ProjectsPanel components.
 * These types are used across SymbolNode, BuildNode, ProjectCard, and DependencyCard.
 */

// Selection type for tracking what's currently selected in the sidebar
export interface Selection {
  type: 'none' | 'project' | 'build' | 'symbol';
  projectId?: string;
  buildId?: string;
  symbolPath?: string;
  label?: string;
}

// Build stage timing
export interface BuildStage {
  name: string;
  displayName?: string;  // User-friendly name
  status: 'pending' | 'running' | 'success' | 'warning' | 'error' | 'skipped';
  duration?: number;  // in seconds (from summary)
  elapsedSeconds?: number;  // in seconds (from live status)
  message?: string;
}

// Last build status (persisted)
export interface LastBuildStatus {
  status: 'success' | 'warning' | 'failed' | 'error';
  timestamp: string;  // ISO timestamp
  elapsedSeconds?: number;
  warnings: number;
  errors: number;
  stages?: BuildStage[];
}

// Build target
export interface BuildTarget {
  id: string;
  name: string;
  entry: string;
  status: 'idle' | 'queued' | 'building' | 'success' | 'error' | 'warning' | 'cancelled';
  errors?: number;
  warnings?: number;
  duration?: number;
  stages?: BuildStage[];
  // Active build tracking
  buildId?: string;  // Active build ID for cancellation
  elapsedSeconds?: number;  // Time elapsed since build started
  currentStage?: string;  // Name of the currently running stage
  queuePosition?: number;  // Position in build queue (1-indexed)
  // TODO: Replace this estimate once builds are defined in the graph
  totalStages?: number;  // Expected total stages for progress (default: 14)
  // Persisted last build status
  lastBuild?: LastBuildStatus;
}

// Project (or package)
export interface Project {
  id: string;
  name: string;
  type: 'project' | 'package';
  root: string;  // Project root path (matches backend 'root' field)
  version?: string;
  latestVersion?: string;  // Latest available version (for update checking)
  installed?: boolean;
  builds: BuildTarget[];
  description?: string;
  summary?: string;  // Short summary/tags from ato.yaml
  homepage?: string;
  repository?: string;
  keywords?: string[];  // For better searching
  publisher?: string;  // Publisher/author of the package
  // Package stats
  downloads?: number;
  versionCount?: number;
  license?: string;
  // Project-level last build status (aggregate of all targets)
  lastBuildStatus?: 'success' | 'warning' | 'failed' | 'error';
  lastBuildTimestamp?: string;
}

// Module definition from API
export interface ModuleDefinition {
  name: string;
  type: 'module' | 'interface' | 'component';
  file: string;
  entry: string;
  line?: number;
  super_type?: string;
}

// Available project for install dropdown
export interface AvailableProject {
  id: string;
  name: string;
  path: string;
  isActive: boolean;
}

// Selected package for detail panel
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
