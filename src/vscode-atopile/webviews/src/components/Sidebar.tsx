/**
 * Sidebar component - Main panel with all sections.
 * Based on the extension-mockup design.
 */

import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { Settings, ChevronDown, FolderOpen, Loader2, AlertCircle, Check, GitBranch, Package, Search } from 'lucide-react';
import type { AppState, Build } from '../types/build';
import { CollapsibleSection } from './CollapsibleSection';
import { ProjectsPanel } from './ProjectsPanel';
import { ProblemsPanel } from './ProblemsPanel';
import { StandardLibraryPanel } from './StandardLibraryPanel';
import { VariablesPanel } from './VariablesPanel';
import { BOMPanel } from './BOMPanel';
import { PackageDetailPanel } from './PackageDetailPanel';
import { BuildQueuePanel, type QueuedBuild } from './BuildQueuePanel';
import { logPerf, logDataSize, startMark } from '../perf';
import './Sidebar.css';
import '../styles.css';

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
function findBuildForTarget(
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

// Default logo as PNG data URI (actual atopile logo)
const DEFAULT_LOGO = `data:image/png;base64,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`;

const vscode = acquireVsCodeApi();

// Send action to extension
const action = (name: string, data?: object) => {
  vscode.postMessage({ type: 'action', action: name, ...data });
};

// Selection type for filtering
interface Selection {
  type: 'none' | 'project' | 'build' | 'symbol';
  projectId?: string;
  buildId?: string;
  symbolId?: string;
  label?: string;
}

// Package type for detail panel
interface SelectedPackage {
  name: string;
  fullName: string;
  version?: string;
  description?: string;
  installed?: boolean;
  availableVersions?: { version: string; released: string }[];
  homepage?: string;
  repository?: string;
}

export function Sidebar() {
  // State from extension
  const [state, setState] = useState<AppState | null>(null);
  
  // Local UI state
  const [selection, setSelection] = useState<Selection>({ type: 'none' });
  // Default collapsed: all sections except 'projects' are collapsed on startup
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set(['buildQueue', 'packages', 'problems', 'stdlib', 'variables', 'bom']));
  const [sectionHeights, setSectionHeights] = useState<Record<string, number>>({});
  const [selectedPackage, setSelectedPackage] = useState<SelectedPackage | null>(null);

  // Stage/build filter for Problems panel
  const [activeStageFilter, setActiveStageFilter] = useState<{
    stageName?: string;
    buildId?: string;
    projectId?: string;
  } | null>(null);

  // Settings dropdown state
  const [showSettings, setShowSettings] = useState(false);

  // Max concurrent builds setting
  // Use navigator.hardwareConcurrency for accurate core count in webview
  const detectedCores = typeof navigator !== 'undefined' ? navigator.hardwareConcurrency || 4 : 4;
  const [maxConcurrentUseDefault, setMaxConcurrentUseDefault] = useState(true);
  const [maxConcurrentValue, setMaxConcurrentValue] = useState(detectedCores);
  const [defaultMaxConcurrent, setDefaultMaxConcurrent] = useState(detectedCores);

  // Branch search state
  const [branchSearchQuery, setBranchSearchQuery] = useState('');
  const [showBranchDropdown, setShowBranchDropdown] = useState(false);
  const branchDropdownRef = useRef<HTMLDivElement>(null);

  // Resize refs
  const resizingRef = useRef<string | null>(null);
  const startYRef = useRef(0);
  const startHeightRef = useRef(0);
  const rafRef = useRef<number | null>(null);  // For RAF throttling

  // Container ref for auto-expand calculation
  const containerRef = useRef<HTMLDivElement>(null);

  // Settings dropdown ref for click-outside detection
  const settingsRef = useRef<HTMLDivElement>(null);

  // Close settings dropdown when clicking outside
  useEffect(() => {
    if (!showSettings) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) {
        setShowSettings(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showSettings]);

  // Fetch max concurrent setting when settings open
  useEffect(() => {
    if (showSettings) {
      action('getMaxConcurrentSetting');
    }
  }, [showSettings]);

  // Close branch dropdown when clicking outside
  useEffect(() => {
    if (!showBranchDropdown) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (branchDropdownRef.current && !branchDropdownRef.current.contains(e.target as Node)) {
        setShowBranchDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showBranchDropdown]);

  // Listen for state from extension
  // Frontend is a pure mirror of server state - no local decision-making
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const msg = event.data;

      if (msg.type === 'state') {
        // Full state replacement (initial connection)
        const endMark = startMark('sidebar:state-receive');
        logDataSize('sidebar:state-payload', msg.data);

        // Validate state has expected structure
        if (msg.data && typeof msg.data === 'object') {
          // Ensure arrays are arrays (not undefined)
          const safeState = {
            ...msg.data,
            projects: Array.isArray(msg.data.projects) ? msg.data.projects : [],
            packages: Array.isArray(msg.data.packages) ? msg.data.packages : [],
            builds: Array.isArray(msg.data.builds) ? msg.data.builds : [],
            queuedBuilds: Array.isArray(msg.data.queuedBuilds) ? msg.data.queuedBuilds : [],
            problems: Array.isArray(msg.data.problems) ? msg.data.problems : [],
            stdlibItems: Array.isArray(msg.data.stdlibItems) ? msg.data.stdlibItems : [],
            logEntries: Array.isArray(msg.data.logEntries) ? msg.data.logEntries : [],
            selectedTargetNames: Array.isArray(msg.data.selectedTargetNames) ? msg.data.selectedTargetNames : [],
            expandedTargets: Array.isArray(msg.data.expandedTargets) ? msg.data.expandedTargets : [],
            enabledLogLevels: Array.isArray(msg.data.enabledLogLevels) ? msg.data.enabledLogLevels : ['INFO', 'WARNING', 'ERROR', 'ALERT'],
          };
          setState(safeState);
        } else {
          console.error('[Sidebar] Invalid state received:', msg.data);
        }

        endMark({
          projects: msg.data?.projects?.length ?? 0,
          builds: msg.data?.builds?.length ?? 0,
          problems: msg.data?.problems?.length ?? 0,
        });
      } else if (msg.type === 'update') {
        // Partial state update - merge changed fields only
        const endMark = startMark('sidebar:state-update');
        const fields = Object.keys(msg.data);
        logDataSize('sidebar:update-payload', msg.data);

        setState(prev => {
          if (!prev) return msg.data;

          // Handle incremental log append (optimization for large log files)
          if (msg.data._appendLogEntries) {
            const newEntries = msg.data._appendLogEntries;
            const { _appendLogEntries, ...rest } = msg.data;
            return {
              ...prev,
              ...rest,
              logEntries: [...(prev.logEntries || []), ...newEntries],
            };
          }

          // Shallow merge - server sends complete field values
          return { ...prev, ...msg.data };
        });

        endMark({ fields: fields.length, fieldNames: fields.join(',') });
      } else if (msg.type === 'action_result' && msg.setting) {
        // Max concurrent builds setting response (from getMaxConcurrentSetting or setMaxConcurrentSetting)
        setMaxConcurrentUseDefault(msg.setting.use_default);
        setMaxConcurrentValue(msg.setting.custom_value || msg.setting.default_value);
        setDefaultMaxConcurrent(msg.setting.default_value);
      } else if (msg.type === 'maxConcurrentSetting') {
        // Legacy: Max concurrent builds setting response (deprecated)
        setMaxConcurrentUseDefault(msg.data.use_default);
        setMaxConcurrentValue(msg.data.custom_value || msg.data.default_value);
        setDefaultMaxConcurrent(msg.data.default_value);
      }
    };
    window.addEventListener('message', handleMessage);
    vscode.postMessage({ type: 'ready' });

    // Trigger initial data refresh after ready signal
    // This ensures problems, packages, and stdlib are loaded
    setTimeout(() => {
      action('refreshProblems');
      action('refreshPackages');
      action('refreshStdlib');
    }, 100);

    return () => window.removeEventListener('message', handleMessage);
  }, []);

  // Auto-expand: detect unused space and cropped sections, expand only as needed
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const sectionIds = ['projects', 'packages', 'problems', 'stdlib', 'variables', 'bom'];
    let debounceTimeoutId: ReturnType<typeof setTimeout> | null = null;

    const checkAutoExpand = () => {
      const containerHeight = container.clientHeight;
      let totalUsedHeight = 0;
      let croppedSectionInfo: { id: string; neededHeight: number; currentHeight: number } | null = null;

      // Calculate total used height and find first cropped section
      for (const id of sectionIds) {
        if (collapsedSections.has(id)) continue;

        const section = container.querySelector(`[data-section-id="${id}"]`) as HTMLElement;
        if (!section) continue;

        const sectionBody = section.querySelector('.section-body') as HTMLElement;
        const titleBar = section.querySelector('.section-title-bar') as HTMLElement;

        if (titleBar) totalUsedHeight += titleBar.offsetHeight;
        if (sectionBody) {
          const currentBodyHeight = sectionBody.offsetHeight;
          const contentHeight = sectionBody.scrollHeight;
          totalUsedHeight += currentBodyHeight;

          // Check if this section is cropped (content larger than visible area)
          const isOverflowing = contentHeight > currentBodyHeight + 5;

          if (isOverflowing && !croppedSectionInfo) {
            croppedSectionInfo = {
              id,
              neededHeight: contentHeight - currentBodyHeight,
              currentHeight: section.offsetHeight,
            };
          }
        }

        // Add resize handle height if present
        const resizeHandle = section.querySelector('.section-resize-handle') as HTMLElement;
        if (resizeHandle) totalUsedHeight += resizeHandle.offsetHeight;

        totalUsedHeight += 1; // border
      }

      // If there's unused space and a cropped section, expand it only as much as needed
      const unusedSpace = containerHeight - totalUsedHeight;
      if (unusedSpace > 20 && croppedSectionInfo) {
        const expandAmount = Math.min(unusedSpace, croppedSectionInfo.neededHeight);
        const newHeight = croppedSectionInfo.currentHeight + expandAmount;

        // Only update if we're actually expanding (avoid infinite loops)
        const currentSetHeight = sectionHeights[croppedSectionInfo.id];
        if (!currentSetHeight || Math.abs(currentSetHeight - newHeight) > 5) {
          setSectionHeights(prev => ({
            ...prev,
            [croppedSectionInfo!.id]: newHeight,
          }));
        }
      }
    };

    // Debounced version that properly cancels previous timeouts
    const debouncedCheckAutoExpand = () => {
      if (debounceTimeoutId !== null) {
        clearTimeout(debounceTimeoutId);
      }
      debounceTimeoutId = setTimeout(checkAutoExpand, 100);
    };

    // Initial check with delay to let layout settle
    const initialTimeoutId = setTimeout(checkAutoExpand, 150);

    // Observe container size changes with proper debouncing
    const resizeObserver = new ResizeObserver(debouncedCheckAutoExpand);
    resizeObserver.observe(container);

    return () => {
      clearTimeout(initialTimeoutId);
      if (debounceTimeoutId !== null) {
        clearTimeout(debounceTimeoutId);
      }
      resizeObserver.disconnect();
    };
  }, [collapsedSections, sectionHeights]);

  // Helper to parse entry point (e.g., "main.ato:App") into symbol structure
  const parseEntryToSymbol = (entry: string) => {
    if (!entry || !entry.includes(':')) return null;
    const [_file, moduleName] = entry.split(':');
    if (!moduleName) return null;
    return {
      name: moduleName,
      type: 'module' as const,
      path: entry,
      // Children would come from build output in the future
      // For now, just show the root module
      children: [],
    };
  };


  // Transform state projects to the format our components expect
  // Memoized to prevent recalculation on every render
  const transformedProjects = useMemo((): any[] => {
    const start = performance.now();
    if (!state?.projects?.length) return [];

    const result = state.projects.map(p => {
      // Transform builds/targets with lastBuild info
      const builds = p.targets.map(t => {
        // UNIFIED: Use shared findBuildForTarget helper
        const build = findBuildForTarget(state.builds, p.name, t.name);
        const rootSymbol = parseEntryToSymbol(t.entry);
        // Get stages from active build or fall back to lastBuild
        const activeStages = build?.stages && build.stages.length > 0 ? build.stages : null;
        const historicalStages = t.lastBuild?.stages;
        const displayStages = activeStages || historicalStages || [];

        return {
          id: t.name,
          name: t.name,
          entry: t.entry,
          status: build?.status === 'failed' ? 'error' : (build?.status || (t.lastBuild?.status === 'failed' ? 'error' : (t.lastBuild?.status || 'idle'))),
          // Include warnings/errors from active build or fall back to lastBuild
          warnings: build?.warnings ?? t.lastBuild?.warnings,
          errors: build?.errors ?? t.lastBuild?.errors,
          // Include elapsed time from active build
          elapsedSeconds: build?.elapsedSeconds,
          duration: t.lastBuild?.elapsedSeconds,
          buildId: build?.buildId,  // For cancel functionality
          // Use active stages if available, otherwise fall back to lastBuild stages
          stages: displayStages.map(s => ({
            ...s,
            status: s.status === 'failed' ? 'error' : s.status,
          })),
          symbols: rootSymbol ? [rootSymbol] : [],
          queuePosition: build?.queuePosition,
          // Include persisted last build status
          lastBuild: t.lastBuild ? {
            status: t.lastBuild.status === 'failed' ? 'error' : t.lastBuild.status,
            timestamp: t.lastBuild.timestamp,
            elapsedSeconds: t.lastBuild.elapsedSeconds,
            warnings: t.lastBuild.warnings,
            errors: t.lastBuild.errors,
            stages: t.lastBuild.stages?.map(s => ({
              name: s.name,
              displayName: s.displayName,
              status: s.status === 'failed' ? 'error' : s.status,
              elapsedSeconds: s.elapsedSeconds,
            })),
          } : undefined,
        };
      });

      // Calculate project-level status from targets
      // Priority: error > warning > success > idle
      let projectStatus: 'success' | 'warning' | 'failed' | 'error' | undefined;
      let mostRecentTimestamp: string | undefined;

      for (const build of builds) {
        // Check active build status first, then fall back to lastBuild
        const status = build.status !== 'idle' ? build.status : build.lastBuild?.status;
        const timestamp = build.lastBuild?.timestamp;

        if (status === 'error' || status === 'failed') {
          projectStatus = 'error';
        } else if (status === 'warning' && projectStatus !== 'error') {
          projectStatus = 'warning';
        } else if (status === 'success' && !projectStatus) {
          projectStatus = 'success';
        }

        // Track most recent timestamp
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
        path: p.root,
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
  }, [state?.projects, state?.builds]);

  // Transform state packages to the format that ProjectsPanel expects
  // UNIFIED: Uses same findBuildForTarget helper as projects
  const transformedPackages = useMemo((): any[] => {
    if (!state?.packages?.length) return [];

    return state.packages
      .filter(pkg => pkg && pkg.identifier && pkg.name)
      .map(pkg => {
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
          };
        });

        return {
          id: pkg.identifier,
          name: pkg.name,
          type: 'package' as const,
          path: `packages/${pkg.identifier}`,
          version: pkg.version || 'unknown',
          latestVersion: pkg.latestVersion,
          installed: pkg.installed ?? false,
          installedIn: pkg.installedIn || [],
          publisher: pkg.publisher || 'unknown',
          summary: pkg.summary || pkg.description || '',
          description: pkg.description || pkg.summary || '',
          homepage: pkg.homepage,
          repository: pkg.repository,
          license: pkg.license,
          keywords: pkg.keywords || [],
          downloads: pkg.downloads,
          versionCount: pkg.versionCount,
          builds: packageBuilds,
        };
      });
  }, [state?.packages, state?.builds]);

  // Combine projects and packages - NO mock data fallback
  const projects = useMemo((): any[] => {
    return [...transformedProjects, ...transformedPackages];
  }, [transformedProjects, transformedPackages]);

  const toggleSection = (sectionId: string) => {
    setCollapsedSections(prev => {
      const next = new Set(prev);
      if (next.has(sectionId)) {
        next.delete(sectionId);
      } else {
        next.add(sectionId);
      }
      return next;
    });
  };

  const handleSelect = (sel: Selection) => {
    setSelection(sel);

    // Notify server when project changes - this triggers BOM fetch etc.
    if (sel.type === 'project' || sel.type === 'build' || sel.type === 'symbol') {
      // Find the project root for this selection
      const project = projects.find(p => p.id === sel.projectId);
      if (project?.root) {
        action('selectProject', { root: project.root });
      }
    }
  };

  const handleBuild = (level: 'project' | 'build' | 'symbol', id: string, label: string) => {
    action('build', { level, id, label });
  };

  const handleCancelBuild = (buildId: string) => {
    action('cancelBuild', { buildId });
  };

  // Cancel build from queue panel (uses build_id format)
  const handleCancelQueuedBuild = (build_id: string) => {
    action('cancelBuild', { buildId: build_id });
  };

  const handleStageFilter = (stageName: string, buildId?: string, projectId?: string) => {
    // Set the stage filter (stageName can be empty for build-level filtering)
    setActiveStageFilter({
      stageName: stageName || undefined,
      buildId,
      projectId
    });

    // Expand the Problems section if collapsed
    setCollapsedSections(prev => {
      const next = new Set(prev);
      next.delete('problems');
      return next;
    });
  };

  const clearStageFilter = () => {
    setActiveStageFilter(null);
  };

  const handleOpenPackageDetail = (pkg: SelectedPackage) => {
    setSelectedPackage(pkg);
    // Fetch detailed package info from the registry
    action('getPackageDetails', { packageId: pkg.fullName });
  };

  const handlePackageInstall = (packageId: string, projectRoot: string) => {
    action('installPackage', { packageId, projectRoot });
  };

  const handleCreateProject = (parentDirectory?: string, name?: string) => {
    action('createProject', { parentDirectory, name });
  };

  // Fetch modules and files when a project is expanded
  const handleProjectExpand = (projectRoot: string) => {
    // Fetch modules if not already loaded
    if (projectRoot && (!state?.projectModules || !state.projectModules[projectRoot])) {
      action('fetchModules', { projectRoot });
    }
    // Fetch files if not already loaded
    if (projectRoot && (!state?.projectFiles || !state.projectFiles[projectRoot])) {
      action('fetchFiles', { projectRoot });
    }
  };

  // Open source file (ato button) - opens the entry point file
  const handleOpenSource = (projectId: string, entry: string) => {
    action('openSource', { projectId, entry });
  };

  // Open in KiCad
  const handleOpenKiCad = (projectId: string, buildId: string) => {
    action('openKiCad', { projectId, buildId });
  };

  // Open layout preview
  const handleOpenLayout = (projectId: string, buildId: string) => {
    action('openLayout', { projectId, buildId });
  };

  // Open 3D viewer
  const handleOpen3D = (projectId: string, buildId: string) => {
    action('open3D', { projectId, buildId });
  };

  const handleResizeStart = useCallback((sectionId: string, e: React.MouseEvent) => {
    e.preventDefault();
    resizingRef.current = sectionId;
    startYRef.current = e.clientY;

    if (sectionHeights[sectionId]) {
      startHeightRef.current = sectionHeights[sectionId];
    } else {
      const section = (e.target as HTMLElement).closest('.collapsible-section');
      startHeightRef.current = section ? section.getBoundingClientRect().height : 200;
    }

    document.addEventListener('mousemove', handleResizeMove);
    document.addEventListener('mouseup', handleResizeEnd);
  }, [sectionHeights]);

  // Throttled resize move using requestAnimationFrame
  const handleResizeMove = useCallback((e: MouseEvent) => {
    if (!resizingRef.current) return;

    // Cancel any pending RAF
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
    }

    // Schedule state update on next frame
    rafRef.current = requestAnimationFrame(() => {
      const delta = e.clientY - startYRef.current;
      const newHeight = Math.max(100, startHeightRef.current + delta);
      setSectionHeights(prev => ({ ...prev, [resizingRef.current!]: newHeight }));
      rafRef.current = null;
    });
  }, []);

  const handleResizeEnd = useCallback(() => {
    // Cancel any pending RAF
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    resizingRef.current = null;
    document.removeEventListener('mousemove', handleResizeMove);
    document.removeEventListener('mouseup', handleResizeEnd);
  }, [handleResizeMove]);

  // Memoize project/package counts - single pass instead of two filters
  const { projectCount, packageCount } = useMemo(() => {
    let projCount = 0;
    let pkgCount = 0;
    for (const p of projects) {
      if (p.type === 'package') pkgCount++;
      else projCount++;
    }
    return { projectCount: projCount, packageCount: pkgCount };
  }, [projects]);

  // STATELESS: Use queuedBuilds directly from state - backend provides display-ready data
  const queuedBuilds = useMemo((): QueuedBuild[] => {
    return (state?.queuedBuilds || []) as QueuedBuild[];
  }, [state?.queuedBuilds]);

  // Pre-index projects by ID for O(1) lookup during filtering
  const projectsById = useMemo(() => {
    return new Map(projects.map(p => [p.id, p]));
  }, [projects]);

  // Use real problems from state - NO mock data fallback
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

    const result = problems.filter(p => {
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
      if (filter.levels?.length > 0 && !filter.levels.includes(p.level)) return false;
      if (filter.buildNames?.length > 0 && p.buildName && !filter.buildNames.includes(p.buildName)) return false;
      if (filter.stageIds?.length > 0 && p.stage && !filter.stageIds.includes(p.stage)) return false;
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

  if (!state) {
    return <div className="sidebar loading">Loading...</div>;
  }

  return (
    <div className="unified-layout">
      {/* Header with logo and settings */}
      <div className="panel-header">
        <div className="header-title">
          <img
            className="logo"
            src={state?.logoUri || DEFAULT_LOGO}
            alt="atopile"
          />
          <span>atopile</span>
          {state?.version && <span className="version-badge">v{state.version}</span>}
        </div>
        <div className="header-actions">
          <div className="settings-dropdown-container" ref={settingsRef}>
            <button
              className={`icon-btn${showSettings ? ' active' : ''}`}
              onClick={() => setShowSettings(!showSettings)}
              title="Settings"
            >
              <Settings size={14} />
            </button>
            {showSettings && (
              <div className="settings-dropdown">
                {/* Installation Progress */}
                {state.atopile?.isInstalling && (
                  <div className="install-progress">
                    <div className="install-progress-header">
                      <Loader2 size={12} className="spinner" />
                      <span>{state.atopile.installProgress?.message || 'Installing...'}</span>
                    </div>
                    {state.atopile.installProgress?.percent !== undefined && (
                      <div className="install-progress-bar">
                        <div
                          className="install-progress-fill"
                          style={{ width: `${state.atopile.installProgress.percent}%` }}
                        />
                      </div>
                    )}
                  </div>
                )}

                {/* Error Display */}
                {state.atopile?.error && (
                  <div className="settings-error">
                    <AlertCircle size={12} />
                    <span>{state.atopile.error}</span>
                  </div>
                )}

                {/* Source Type Selector */}
                <div className="settings-group">
                  <label className="settings-label">
                    <span className="settings-label-title">Source</span>
                  </label>
                  <div className="settings-source-buttons">
                    <button
                      className={`source-btn${state.atopile?.source === 'release' ? ' active' : ''}`}
                      onClick={() => action('setAtopileSource', { source: 'release' })}
                      disabled={state.atopile?.isInstalling}
                      title="Use a released version from PyPI"
                    >
                      <Package size={12} />
                      Release
                    </button>
                    <button
                      className={`source-btn${state.atopile?.source === 'branch' ? ' active' : ''}`}
                      onClick={() => action('setAtopileSource', { source: 'branch' })}
                      disabled={state.atopile?.isInstalling}
                      title="Use a git branch from GitHub"
                    >
                      <GitBranch size={12} />
                      Branch
                    </button>
                    <button
                      className={`source-btn${state.atopile?.source === 'local' ? ' active' : ''}`}
                      onClick={() => action('setAtopileSource', { source: 'local' })}
                      disabled={state.atopile?.isInstalling}
                      title="Use a local installation"
                    >
                      <FolderOpen size={12} />
                      Local
                    </button>
                  </div>
                </div>

                {/* Version Selector (when using release) */}
                {state.atopile?.source === 'release' && (
                  <div className="settings-group">
                    <label className="settings-label">
                      <span className="settings-label-title">Version</span>
                    </label>
                    <div className="settings-select-wrapper">
                      <select
                        className="settings-select"
                        value={state.atopile?.currentVersion || ''}
                        onChange={(e) => {
                          action('setAtopileVersion', { version: e.target.value });
                        }}
                        disabled={state.atopile?.isInstalling}
                      >
                        {(state.atopile?.availableVersions || []).map((v) => (
                          <option key={v} value={v}>
                            {v}{v === state.atopile?.availableVersions?.[0] ? ' (latest)' : ''}
                          </option>
                        ))}
                      </select>
                      <ChevronDown size={12} className="select-chevron" />
                    </div>
                  </div>
                )}

                {/* Branch Selector (when using branch) */}
                {state.atopile?.source === 'branch' && (
                  <div className="settings-group">
                    <label className="settings-label">
                      <span className="settings-label-title">Branch</span>
                    </label>
                    <div className="branch-search-container" ref={branchDropdownRef}>
                      <div className="branch-search-input-wrapper">
                        <Search size={12} className="branch-search-icon" />
                        <input
                          type="text"
                          className="branch-search-input"
                          placeholder="Search branches..."
                          value={branchSearchQuery}
                          onChange={(e) => {
                            setBranchSearchQuery(e.target.value);
                            setShowBranchDropdown(true);
                          }}
                          onFocus={() => setShowBranchDropdown(true)}
                          disabled={state.atopile?.isInstalling}
                        />
                        {state.atopile?.branch && !branchSearchQuery && (
                          <span className="branch-current-value">{state.atopile.branch}</span>
                        )}
                      </div>
                      {showBranchDropdown && (
                        <div className="branch-dropdown">
                          {(state.atopile?.availableBranches || ['main', 'develop'])
                            .filter(b => !branchSearchQuery || b.toLowerCase().includes(branchSearchQuery.toLowerCase()))
                            .slice(0, 15)
                            .map((b) => (
                              <button
                                key={b}
                                className={`branch-option${b === state.atopile?.branch ? ' active' : ''}`}
                                onClick={() => {
                                  action('setAtopieBranch', { branch: b });
                                  setBranchSearchQuery('');
                                  setShowBranchDropdown(false);
                                }}
                              >
                                <GitBranch size={12} />
                                <span>{b}</span>
                                {b === 'main' && <span className="branch-tag">default</span>}
                              </button>
                            ))}
                          {branchSearchQuery &&
                            !(state.atopile?.availableBranches || []).some(b =>
                              b.toLowerCase().includes(branchSearchQuery.toLowerCase())
                            ) && (
                            <div className="branch-no-results">No branches match "{branchSearchQuery}"</div>
                          )}
                        </div>
                      )}
                    </div>
                    <span className="settings-hint">
                      Installs from git+https://github.com/atopile/atopile.git@{state.atopile?.branch || 'main'}
                    </span>
                  </div>
                )}

                {/* Local Path Input (when using local) */}
                {state.atopile?.source === 'local' && (
                  <div className="settings-group local-path-section">
                    <label className="settings-label">
                      <span className="settings-label-title">Local Path</span>
                    </label>

                    {/* Detected installations */}
                    {(state.atopile?.detectedInstallations?.length ?? 0) > 0 && (
                      <div className="detected-installations">
                        <span className="detected-label">Detected:</span>
                        {state.atopile?.detectedInstallations?.map((inst, i) => (
                          <button
                            key={i}
                            className={`detected-item${state.atopile?.localPath === inst.path ? ' active' : ''}`}
                            onClick={() => action('setAtopileLocalPath', { path: inst.path })}
                            title={inst.path}
                          >
                            <span className="detected-source">{inst.source}</span>
                            {inst.version && <span className="detected-version">v{inst.version}</span>}
                          </button>
                        ))}
                      </div>
                    )}

                    {/* Manual path input */}
                    <div className="settings-path-input">
                      <input
                        type="text"
                        className="settings-input"
                        placeholder="/path/to/atopile or ato"
                        value={state.atopile?.localPath || ''}
                        onChange={(e) => {
                          action('setAtopileLocalPath', { path: e.target.value });
                        }}
                      />
                      <button
                        className="path-browse-btn"
                        onClick={() => action('browseAtopilePath')}
                        title="Browse..."
                      >
                        <FolderOpen size={12} />
                      </button>
                    </div>
                  </div>
                )}

                {/* Current Status */}
                {!state.atopile?.isInstalling && state.atopile?.currentVersion && (
                  <div className="settings-status">
                    <Check size={12} className="status-ok" />
                    <span>
                      {state.atopile.source === 'local'
                        ? `Using local: ${state.atopile.localPath?.split('/').pop() || 'atopile'}`
                        : `v${state.atopile.currentVersion} installed`
                      }
                    </span>
                  </div>
                )}

                <div className="settings-divider" />

                {/* Parallel Builds Setting */}
                <div className="settings-group">
                  <div className="settings-row">
                    <span className="settings-label-title">Parallel builds</span>
                    <div className="settings-inline-control">
                      {maxConcurrentUseDefault ? (
                        <button
                          className="settings-value-btn"
                          onClick={() => setMaxConcurrentUseDefault(false)}
                          title="Click to set custom limit"
                        >
                          Auto ({defaultMaxConcurrent})
                        </button>
                      ) : (
                        <div className="settings-custom-input">
                          <input
                            type="number"
                            className="settings-input small"
                            min={1}
                            max={32}
                            value={maxConcurrentValue}
                            onChange={(e) => {
                              const value = Math.max(1, Math.min(32, parseInt(e.target.value) || 1));
                              setMaxConcurrentValue(value);
                              action('setMaxConcurrentSetting', {
                                useDefault: false,
                                customValue: value
                              });
                            }}
                          />
                          <button
                            className="settings-reset-btn"
                            onClick={() => {
                              setMaxConcurrentUseDefault(true);
                              action('setMaxConcurrentSetting', {
                                useDefault: true,
                                customValue: null
                              });
                            }}
                            title="Reset to auto"
                          >
                            Auto
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

              </div>
            )}
          </div>
        </div>
      </div>

      <div className="panel-sections" ref={containerRef}>
        {/* Projects Section - auto-size with max height, or use manual height if user resized */}
        <CollapsibleSection
          id="projects"
          title="Projects"
          badge={projectCount}
          collapsed={collapsedSections.has('projects')}
          onToggle={() => toggleSection('projects')}
          height={sectionHeights.projects}
          maxHeight={!sectionHeights.projects ? 400 : undefined}
          onResizeStart={(e) => handleResizeStart('projects', e)}
        >
          <ProjectsPanel
            selection={selection}
            onSelect={handleSelect}
            onBuild={handleBuild}
            onCancelBuild={handleCancelBuild}
            onStageFilter={handleStageFilter}
            onCreateProject={handleCreateProject}
            onProjectExpand={handleProjectExpand}
            onOpenSource={handleOpenSource}
            onOpenKiCad={handleOpenKiCad}
            onOpenLayout={handleOpenLayout}
            onOpen3D={handleOpen3D}
            onFileClick={(projectId, filePath) => {
              // Open the file in the editor
              // Get full path from project root
              const project = projects.find(p => p.id === projectId);
              if (project) {
                const fullPath = `${project.path}/${filePath}`;
                action('openFile', { file: fullPath });
              }
            }}
            filterType="projects"
            projects={projects}
            projectModules={state?.projectModules || {}}
            projectFiles={state?.projectFiles || {}}
          />
        </CollapsibleSection>

        {/* Build Queue Section - only visible when there are queued builds */}
        {queuedBuilds.length > 0 && (
          <CollapsibleSection
            id="buildQueue"
            title="Build Queue"
            badge={queuedBuilds.length}
            badgeType="count"
            collapsed={collapsedSections.has('buildQueue')}
            onToggle={() => toggleSection('buildQueue')}
            height={collapsedSections.has('buildQueue') ? undefined : sectionHeights.buildQueue}
            onResizeStart={(e) => handleResizeStart('buildQueue', e)}
          >
            <BuildQueuePanel
              builds={queuedBuilds}
              onCancelBuild={handleCancelQueuedBuild}
            />
          </CollapsibleSection>
        )}

        {/* Packages Section - auto-size with max height, or use manual height if user resized */}
        <CollapsibleSection
          id="packages"
          title="Packages"
          badge={packageCount}
          warningMessage={state?.packagesError || null}
          collapsed={collapsedSections.has('packages')}
          onToggle={() => toggleSection('packages')}
          height={sectionHeights.packages}
          maxHeight={!sectionHeights.packages ? 400 : undefined}
          onResizeStart={(e) => handleResizeStart('packages', e)}
        >
          <ProjectsPanel
            selection={selection}
            onSelect={handleSelect}
            onBuild={handleBuild}
            onCancelBuild={handleCancelBuild}
            onStageFilter={handleStageFilter}
            onOpenPackageDetail={handleOpenPackageDetail}
            onPackageInstall={handlePackageInstall}
            onOpenSource={handleOpenSource}
            onOpenKiCad={handleOpenKiCad}
            onOpenLayout={handleOpenLayout}
            onOpen3D={handleOpen3D}
            filterType="packages"
            projects={projects}
          />
        </CollapsibleSection>

        {/* Problems Section */}
        <CollapsibleSection
          id="problems"
          title={activeStageFilter ? `Problems: ${activeStageFilter.stageName || activeStageFilter.buildId || 'Filtered'}` : 'Problems'}
          badge={activeStageFilter ? filteredProblems.length : (totalErrors + totalWarnings)}
          badgeType={activeStageFilter ? 'filter' : 'count'}
          errorCount={activeStageFilter ? undefined : totalErrors}
          warningCount={activeStageFilter ? undefined : totalWarnings}
          collapsed={collapsedSections.has('problems')}
          onToggle={() => toggleSection('problems')}
          onClearFilter={activeStageFilter ? clearStageFilter : undefined}
          height={collapsedSections.has('problems') ? undefined : sectionHeights.problems}
          onResizeStart={(e) => handleResizeStart('problems', e)}
        >
          <ProblemsPanel
            problems={filteredProblems}
            filter={state?.problemFilter}
            selection={selection}
            onSelectionChange={setSelection}
            projects={projects}
            onProblemClick={(problem) => {
              // Navigate to file location
              action('openFile', { file: problem.file, line: problem.line, column: problem.column });
            }}
            onToggleLevelFilter={(level) => {
              action('toggleProblemLevelFilter', { level });
            }}
          />
        </CollapsibleSection>

        {/* Standard Library Section */}
        <CollapsibleSection
          id="stdlib"
          title="Standard Library"
          badge={state?.stdlibItems?.length || 0}
          collapsed={collapsedSections.has('stdlib')}
          onToggle={() => toggleSection('stdlib')}
          height={collapsedSections.has('stdlib') ? undefined : sectionHeights.stdlib}
          onResizeStart={(e) => handleResizeStart('stdlib', e)}
        >
          <StandardLibraryPanel
            items={state?.stdlibItems}
            isLoading={state?.isLoadingStdlib}
            onRefresh={() => action('refreshStdlib')}
          />
        </CollapsibleSection>

        {/* Variables Section */}
        <CollapsibleSection
          id="variables"
          title="Variables"
          badge={(() => {
            // Count total variables from current data
            const varData = state?.currentVariablesData
            if (!varData?.nodes) return 0
            const countVars = (nodes: typeof varData.nodes): number => {
              let count = 0
              for (const n of nodes) {
                count += n.variables?.length || 0
                if (n.children) count += countVars(n.children)
              }
              return count
            }
            return countVars(varData.nodes)
          })()}
          collapsed={collapsedSections.has('variables')}
          onToggle={() => toggleSection('variables')}
          height={collapsedSections.has('variables') ? undefined : sectionHeights.variables}
          onResizeStart={(e) => handleResizeStart('variables', e)}
        >
          <VariablesPanel
            variablesData={state?.currentVariablesData}
            isLoading={state?.isLoadingVariables}
            error={state?.variablesError}
            onBuild={() => action('build')}
          />
        </CollapsibleSection>

        {/* BOM Section */}
        <CollapsibleSection
          id="bom"
          title="BOM"
          badge={state?.bomData?.components?.length ?? 0}
          warningCount={
            state?.bomData?.components
              ? state.bomData.components.filter(c => c.stock !== null && c.stock === 0).length
              : 0
          }
          collapsed={collapsedSections.has('bom')}
          onToggle={() => toggleSection('bom')}
          height={collapsedSections.has('bom') ? undefined : sectionHeights.bom}
          onResizeStart={(e) => handleResizeStart('bom', e)}
        >
          <BOMPanel
            bomData={state?.bomData}
            isLoading={state?.isLoadingBom}
            error={state?.bomError}
            onGoToSource={(path, line) => {
              action('openFile', { file: path, line });
            }}
          />
        </CollapsibleSection>
      </div>

      {/* Detail Panel (slides in when package selected) */}
      {selectedPackage && (
        <div className="detail-panel-container">
          <PackageDetailPanel
            package={selectedPackage}
            packageDetails={state?.selectedPackageDetails || null}
            isLoading={state?.isLoadingPackageDetails || false}
            error={state?.packageDetailsError || null}
            onClose={() => {
              setSelectedPackage(null);
              action('clearPackageDetails');
            }}
            onInstall={(version) => {
              // Install to the currently selected project
              const projectRoot = state?.selectedProjectRoot || (state?.projects?.[0]?.root);
              if (projectRoot) {
                action('installPackage', {
                  packageId: selectedPackage.fullName,
                  projectRoot,
                  version
                });
              }
            }}
            onBuild={(entry?: string) => {
              // Build the package (installs if needed, then builds)
              const projectRoot = state?.selectedProjectRoot || (state?.projects?.[0]?.root);
              if (projectRoot) {
                action('buildPackage', {
                  packageId: selectedPackage.fullName,
                  projectRoot,
                  entry
                });
              }
            }}
          />
        </div>
      )}
    </div>
  );
}
