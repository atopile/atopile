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
  Problem,
  LogEntry,
  ModuleDefinition,
  FileTreeNode,
  VariablesData,
  ProjectDependency,
} from '../types/build';

// Declare window properties for TypeScript
declare global {
  interface Window {
    __ATOPILE_API_URL__?: string;
    __ATOPILE_WS_URL__?: string;
  }
}

// Base URL - configurable for development or injected by extension
const BASE_URL =
  (typeof window !== 'undefined' && window.__ATOPILE_API_URL__) ||
  import.meta.env.VITE_API_URL ||
  'http://localhost:8501';

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

interface LogsResponse {
  logs: LogEntry[];
  total: number;
  hasMore: boolean;
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
      fetchJSON<{ status: string; project_root: string; targets: string[]; return_code: number | null; error: string | null; stages: unknown[] }>(
        `/api/build/${buildId}/status`
      ),

    start: (projectRoot: string, targets: string[] = [], options?: { entry?: string; standalone?: boolean; frozen?: boolean }) =>
      fetchJSON<{ success: boolean; message: string; build_id: string }>('/api/build', {
        method: 'POST',
        body: JSON.stringify({
          project_root: projectRoot,
          targets,
          ...options,
        }),
      }),

    cancel: (buildId: string) =>
      fetchJSON<{ success: boolean; message: string }>(`/api/build/${buildId}/cancel`, { method: 'POST' }),
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
          identifier,
          project_root: projectRoot,
          version,
        }),
      }),

    remove: (identifier: string, projectRoot: string) =>
      fetchJSON<{ success: boolean; message: string }>('/api/packages/remove', {
        method: 'POST',
        body: JSON.stringify({
          identifier,
          project_root: projectRoot,
        }),
      }),
  },

  // Logs
  logs: {
    query: (options?: {
      buildName?: string;
      projectName?: string;
      levels?: string[];
      search?: string;
      limit?: number;
      offset?: number;
    }) => {
      const params = new URLSearchParams();
      if (options?.buildName) params.set('build_name', options.buildName);
      if (options?.projectName) params.set('project_name', options.projectName);
      if (options?.levels) params.set('levels', options.levels.join(','));
      if (options?.search) params.set('search', options.search);
      if (options?.limit) params.set('limit', String(options.limit));
      if (options?.offset) params.set('offset', String(options.offset));
      return fetchJSON<{ logs: LogEntry[]; total: number; max_id: number; has_more: boolean }>(
        `/api/logs/query?${params}`
      );
    },

    counts: (buildName?: string, projectName?: string) => {
      const params = new URLSearchParams();
      if (buildName) params.set('build_name', buildName);
      if (projectName) params.set('project_name', projectName);
      return fetchJSON<{
        counts: { DEBUG: number; INFO: number; WARNING: number; ERROR: number; ALERT: number };
        total: number;
        has_more: boolean;
      }>(`/api/logs/counts?${params}`);
    },
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
  },

  dependencies: {
    list: (projectRoot: string) =>
      fetchJSON<DependenciesResponse>(
        `/api/dependencies?project_root=${encodeURIComponent(projectRoot)}`
      ),
  },
};

export default api;
