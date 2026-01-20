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
import '../mockup.css';

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
  builds: Build[],
  projectName: string,
  targetName: string
): Build | undefined {
  // 1. Find active build (building/queued) for this specific target
  let build = builds.find(b => {
    if (b.status !== 'building' && b.status !== 'queued') return false;

    // Match by project (use project_name or derive from project_root)
    const buildProjectName = b.project_name || (b.project_root ? b.project_root.split('/').pop() : null);
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
      (b.project_name === projectName || b.project_name === null)
    );
  }

  return build;
}

// Default logo as SVG data URI for dev mode fallback
const DEFAULT_LOGO = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ccircle cx='50' cy='50' r='45' fill='%23f95015'/%3E%3Ctext x='50' y='65' font-size='50' font-weight='bold' fill='white' text-anchor='middle' font-family='system-ui'%3Ea%3C/text%3E%3C/svg%3E`;

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
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set(['problems', 'stdlib', 'variables', 'bom']));
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
        setState(msg.data);
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
      } else if (msg.type === 'maxConcurrentSetting') {
        // Max concurrent builds setting response
        setMaxConcurrentUseDefault(msg.data.use_default);
        setMaxConcurrentValue(msg.data.custom_value || msg.data.default_value);
        setDefaultMaxConcurrent(msg.data.default_value);
      }
    };
    window.addEventListener('message', handleMessage);
    vscode.postMessage({ type: 'ready' });
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
      // Transform builds/targets with last_build info
      const builds = p.targets.map(t => {
        // UNIFIED: Use shared findBuildForTarget helper
        const build = findBuildForTarget(state.builds, p.name, t.name);
        const rootSymbol = parseEntryToSymbol(t.entry);
        // Get stages from active build or fall back to last_build
        const activeStages = build?.stages && build.stages.length > 0 ? build.stages : null;
        const historicalStages = t.last_build?.stages;
        const displayStages = activeStages || historicalStages || [];
        
        return {
          id: t.name,
          name: t.name,
          entry: t.entry,
          status: build?.status === 'failed' ? 'error' : (build?.status || (t.last_build?.status === 'failed' ? 'error' : (t.last_build?.status || 'idle'))),
          // Include warnings/errors from active build or fall back to last_build
          warnings: build?.warnings ?? t.last_build?.warnings,
          errors: build?.errors ?? t.last_build?.errors,
          // Include elapsed time from active build
          elapsedSeconds: build?.elapsed_seconds,
          duration: t.last_build?.elapsed_seconds,
          buildId: (build as any)?.build_id,  // For cancel functionality
          // Use active stages if available, otherwise fall back to last_build stages
          stages: displayStages.map(s => ({
            ...s,
            status: s.status === 'failed' ? 'error' : s.status,
          })),
          symbols: rootSymbol ? [rootSymbol] : [],
          queuePosition: build?.queue_position,
          // Include persisted last build status
          lastBuild: t.last_build ? {
            status: t.last_build.status === 'failed' ? 'error' : t.last_build.status,
            timestamp: t.last_build.timestamp,
            elapsed_seconds: t.last_build.elapsed_seconds,
            warnings: t.last_build.warnings,
            errors: t.last_build.errors,
            stages: t.last_build.stages?.map(s => ({
              name: s.name,
              display_name: s.display_name,
              status: s.status === 'failed' ? 'error' : s.status,
              elapsed_seconds: s.elapsed_seconds,
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
      builds: state.builds.length,
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
            buildId: build?.build_id,
            elapsedSeconds: build?.elapsed_seconds,
            warnings: build?.warnings,
            errors: build?.errors,
            stages: build?.stages || [],
            queuePosition: build?.queue_position,
          };
        });

        return {
          id: pkg.identifier,
          name: pkg.name,
          type: 'package' as const,
          path: `packages/${pkg.identifier}`,
          version: pkg.version || 'unknown',
          latestVersion: pkg.latest_version,
          installed: pkg.installed ?? false,
          installedIn: pkg.installed_in || [],
          publisher: pkg.publisher || 'unknown',
          summary: pkg.summary || pkg.description || '',
          description: pkg.description || pkg.summary || '',
          homepage: pkg.homepage,
          repository: pkg.repository,
          license: pkg.license,
          keywords: pkg.keywords || [],
          downloads: pkg.downloads,
          versionCount: pkg.version_count,
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

  // Fetch modules when a project is expanded (for entry point picker)
  const handleProjectExpand = (projectRoot: string) => {
    // Fetch modules if not already loaded
    if (projectRoot && (!state?.projectModules || !state.projectModules[projectRoot])) {
      action('fetchModules', { projectRoot });
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
            filterType="projects"
            projects={projects}
            projectModules={state?.projectModules || {}}
          />
        </CollapsibleSection>

        {/* Build Queue Section - always visible */}
        <CollapsibleSection
          id="buildQueue"
          title="Build Queue"
          badge={queuedBuilds.length > 0 ? queuedBuilds.length : undefined}
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

        {/* Packages Section - auto-size with max height, or use manual height if user resized */}
        <CollapsibleSection
          id="packages"
          title="Packages"
          badge={packageCount}
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
            selection={selection}
            onSelectionChange={setSelection}
            projects={projects}
            bomData={state?.bomData}
            isLoading={state?.isLoadingBOM}
            error={state?.bomError}
            onRefresh={() => {
              // Send the currently selected project root to fetch BOM for
              const projectRoot = state?.selectedProjectRoot || (state?.projects?.[0]?.root);
              action('refreshBOM', { projectRoot, target: 'default' });
            }}
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
