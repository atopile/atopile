/**
 * HTTP API client for direct communication with the Python backend.
 *
 * The UI Server connects directly to the backend - no VS Code extension middleman.
 * Base URL can be configured via environment variable for development.
 */

import type {
  Project,
  Build,
  PackageInfo,
  PackageDetails,
  StdLibItem,
  BOMData,
  LcscPartsResponse,
  Problem,
  ModuleDefinition,
  ModuleChild,
  FileTreeNode,
  VariablesData,
  ProjectDependency,
} from '../types/build';
import { API_URL } from './config';

// Base URL - from centralized config
const BASE_URL = API_URL;

/**
 * Custom error class for API errors.
 */
export class APIError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: unknown
  ) {
    super(message);
    this.name = 'APIError';
  }
}

/**
 * Generic fetch wrapper with error handling.
 */
async function fetchJSON<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = response.statusText;
    }
    throw new APIError(
      response.status,
      typeof detail === 'object' && detail && 'detail' in detail
        ? String((detail as { detail: unknown }).detail)
        : response.statusText,
      detail
    );
  }

  // Handle empty responses
  const text = await response.text();
  if (!text) return {} as T;

  return JSON.parse(text);
}

// Response types
interface ProjectsResponse {
  projects: Project[];
}

interface BuildsResponse {
  builds: Build[];
}

interface ActiveBuildsResponse {
  builds: Build[];
}

interface PackagesResponse {
  packages: PackageInfo[];
}

interface StdLibResponse {
  items: StdLibItem[];
}

interface ProblemsResponse {
  problems: Problem[];
}

interface LogBuildId {
  build_id: string;
  last_timestamp: string | null;
  log_count: number;
}

interface ModulesResponse {
  modules: ModuleDefinition[];
}

interface FilesResponse {
  files: FileTreeNode[];
}

interface DependenciesResponse {
  dependencies: ProjectDependency[];
}

/**
 * API client with typed methods for all backend endpoints.
 */
export const api = {
  // Health check
  health: () => fetchJSON<{ status: string }>('/health'),

  // Projects
  projects: {
    list: () => fetchJSON<ProjectsResponse>('/api/projects'),
  },

  // Builds
  builds: {
    history: () => fetchJSON<BuildsResponse>('/api/builds/history'),

    active: () => fetchJSON<ActiveBuildsResponse>('/api/builds/active'),

    queue: () => fetchJSON<{ queue: Build[] }>('/api/builds/queue'),

    status: (buildId: string) =>
      fetchJSON<{ build_id: string; target: string; status: string; project_root: string; return_code: number | null; error: string | null }>(
        `/api/build/${buildId}/status`
      ),

    start: (projectRoot: string, targets: string[] = [], options?: { entry?: string; standalone?: boolean; frozen?: boolean }) =>
      fetchJSON<{
        success: boolean;
        message: string;
        build_targets: { target: string; build_id: string }[];
      }>('/api/build', {
        method: 'POST',
        body: JSON.stringify({
          project_root: projectRoot,
          targets,
          ...options,
        }),
      }),

    cancel: (buildId: string) =>
      fetchJSON<{ success: boolean; message: string }>(`/api/build/${buildId}/cancel`, { method: 'POST' }),

    // Build-ID based lookups
    info: (buildId: string) =>
      fetchJSON<{
        build_id: string;
        project_root: string;
        target: string;
        started_at: number;
        completed_at: number | null;
        status: string;
        duration: number | null;
        warnings: number;
        errors: number;
      }>(`/api/build/${buildId}/info`),

    byProject: (projectRoot?: string, target?: string, limit: number = 50) => {
      const params = new URLSearchParams();
      if (projectRoot) params.set('project_root', projectRoot);
      if (target) params.set('target', target);
      params.set('limit', String(limit));
      return fetchJSON<{ builds: Build[]; total: number }>(`/api/builds?${params}`);
    },

    // Build-ID based artifact retrieval
    bom: (buildId: string) => fetchJSON<BOMData>(`/api/build/${buildId}/bom`),

    variables: (buildId: string) => fetchJSON<VariablesData>(`/api/build/${buildId}/variables`),
  },

  // Logs
  logs: {
    buildIds: (limit: number = 200) =>
      fetchJSON<{ builds: LogBuildId[] }>(`/api/logs/build-ids?limit=${limit}`),
  },

  // Packages
  packages: {
    list: () => fetchJSON<PackagesResponse>('/api/packages'),

    summary: () => fetchJSON<{ packages: PackageInfo[]; total: number }>('/api/packages/summary'),

    search: (query: string) =>
      fetchJSON<{ packages: PackageInfo[]; total: number; query: string }>(
        `/api/registry/search?q=${encodeURIComponent(query)}`
      ),

    details: (identifier: string) =>
      fetchJSON<PackageDetails>(
        `/api/packages/${encodeURIComponent(identifier)}/details`
      ),

    install: (identifier: string, projectRoot: string, version?: string) =>
      fetchJSON<{ success: boolean; message: string }>('/api/packages/install', {
        method: 'POST',
        body: JSON.stringify({
          package_identifier: identifier,
          project_root: projectRoot,
          version,
        }),
      }),

    remove: (identifier: string, projectRoot: string) =>
      fetchJSON<{ success: boolean; message: string }>('/api/packages/remove', {
        method: 'POST',
        body: JSON.stringify({
          package_identifier: identifier,
          project_root: projectRoot,
        }),
      }),
  },

  // Problems
  problems: {
    list: (options?: { projectRoot?: string; buildName?: string; level?: string }) => {
      const params = new URLSearchParams();
      if (options?.projectRoot) params.set('project_root', options.projectRoot);
      if (options?.buildName) params.set('build_name', options.buildName);
      if (options?.level) params.set('level', options.level);
      return fetchJSON<ProblemsResponse>(`/api/problems?${params}`);
    },
  },

  // Standard Library
  stdlib: {
    list: () => fetchJSON<StdLibResponse>('/api/stdlib'),
  },

  // BOM
  bom: {
    get: (projectRoot: string, targetName: string) =>
      fetchJSON<BOMData>(
        `/api/bom?project_root=${encodeURIComponent(projectRoot)}&target=${encodeURIComponent(targetName)}`
      ),
    targets: (projectRoot: string) =>
      fetchJSON<{ targets: string[] }>(
        `/api/bom/targets?project_root=${encodeURIComponent(projectRoot)}`
      ),
  },

  // Variables
  variables: {
    get: (projectRoot: string, targetName: string) =>
      fetchJSON<VariablesData>(
        `/api/variables?project_root=${encodeURIComponent(projectRoot)}&target=${encodeURIComponent(targetName)}`
      ),
    targets: (projectRoot: string) =>
      fetchJSON<{ targets: string[] }>(
        `/api/variables/targets?project_root=${encodeURIComponent(projectRoot)}`
      ),
  },

  // Parts (LCSC metadata)
  parts: {
    lcsc: (lcscIds: string[], options?: { projectRoot?: string; target?: string | null }) =>
      fetchJSON<LcscPartsResponse>('/api/parts/lcsc', {
        method: 'POST',
        body: JSON.stringify({
          lcsc_ids: lcscIds,
          project_root: options?.projectRoot,
          target: options?.target ?? undefined,
        }),
      }),
  },

  // Project files/modules
  files: {
    list: (projectRoot: string) =>
      fetchJSON<FilesResponse>(
        `/api/files?project_root=${encodeURIComponent(projectRoot)}`
      ),
  },

  modules: {
    list: (projectRoot: string) =>
      fetchJSON<ModulesResponse>(
        `/api/modules?project_root=${encodeURIComponent(projectRoot)}`
      ),
    getChildren: (projectRoot: string, entryPoint: string, maxDepth: number = 2) =>
      fetchJSON<ModuleChild[]>(
        `/api/module/children?project_root=${encodeURIComponent(projectRoot)}&entry_point=${encodeURIComponent(entryPoint)}&max_depth=${maxDepth}`
      ),
  },

  dependencies: {
    list: (projectRoot: string) =>
      fetchJSON<DependenciesResponse>(
        `/api/dependencies?project_root=${encodeURIComponent(projectRoot)}`
      ),
    updateVersion: (projectRoot: string, identifier: string, newVersion: string) =>
      fetchJSON<{ success: boolean; message: string }>('/api/dependency/update', {
        method: 'POST',
        body: JSON.stringify({
          project_root: projectRoot,
          identifier,
          new_version: newVersion,
        }),
      }),
  },

  // Build targets
  buildTargets: {
    add: (projectRoot: string, name: string, entry: string) =>
      fetchJSON<{ success: boolean; message: string; target?: { name: string; entry: string; root: string } }>(
        '/api/build-target/add',
        {
          method: 'POST',
          body: JSON.stringify({
            project_root: projectRoot,
            name,
            entry,
          }),
        }
      ),
    update: (projectRoot: string, oldName: string, newName?: string, newEntry?: string) =>
      fetchJSON<{ success: boolean; message: string; target?: { name: string; entry: string; root: string } }>(
        '/api/build-target/update',
        {
          method: 'POST',
          body: JSON.stringify({
            project_root: projectRoot,
            old_name: oldName,
            new_name: newName,
            new_entry: newEntry,
          }),
        }
      ),
    delete: (projectRoot: string, name: string) =>
      fetchJSON<{ success: boolean; message: string }>('/api/build-target/delete', {
        method: 'POST',
        body: JSON.stringify({
          project_root: projectRoot,
          name,
        }),
      }),
  },
};

export default api;
