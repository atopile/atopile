/**
 * ProjectsPanelConnected - Connected version using hooks.
 *
 * This is a simplified connected component that provides hook-based
 * state management to the existing ProjectsPanel component.
 *
 * Note: The full ProjectsPanel has many callback props for various actions.
 * This connected version provides the core functionality - additional
 * callbacks can be added as needed.
 */

import { useCallback } from 'react';
import { useProjects, useBuilds } from '../hooks';
import { useStore } from '../store';
import { api } from '../api/client';
import './ProjectsPanelConnected.css';

// Selection type matching ProjectsPanel
interface Selection {
  type: 'none' | 'project' | 'build' | 'symbol';
  projectId?: string;
  buildId?: string;
  symbolPath?: string;
  label?: string;
}

// Build symbol type
interface BuildSymbol {
  name: string;
  type: 'module' | 'interface' | 'component' | 'parameter';
  path: string;
  children?: BuildSymbol[];
  hasErrors?: boolean;
  hasWarnings?: boolean;
}

// Build target type for the panel
interface BuildTarget {
  id: string;
  name: string;
  entry: string;
  status: 'idle' | 'queued' | 'building' | 'success' | 'error' | 'warning' | 'cancelled';
  errors?: number;
  warnings?: number;
  duration?: number;
  symbols?: BuildSymbol[];
  buildId?: string;
  elapsedSeconds?: number;
  currentStage?: string;
  queuePosition?: number;
}

// Project type for the panel
interface Project {
  id: string;
  name: string;
  type: 'project' | 'package';
  path: string;
  version?: string;
  latestVersion?: string;
  installed?: boolean;
  builds: BuildTarget[];
  description?: string;
  summary?: string;
  homepage?: string;
  repository?: string;
  keywords?: string[];
  publisher?: string;
  downloads?: number;
  versionCount?: number;
  license?: string;
  lastBuildStatus?: 'success' | 'warning' | 'failed' | 'error';
  lastBuildTimestamp?: string;
}

// Simplified ProjectsPanel that uses hooks internally
export function ProjectsPanelConnected() {
  const {
    projects,
    selectedProjectRoot,
    selectedTargetNames,
    expandedTargets,
    selectProject,
    toggleTarget,
    toggleTargetExpanded,
  } = useProjects();

  const { startBuild, cancelBuild, queuedBuilds } = useBuilds();
  const projectModules = useStore((state) => state.projectModules);
  const projectFiles = useStore((state) => state.projectFiles);
  const projectDependencies = useStore((state) => state.projectDependencies);

  // Current selection state
  const selection: Selection = selectedProjectRoot
    ? { type: 'project', projectId: selectedProjectRoot }
    : { type: 'none' };

  // Transform store projects to panel format
  const transformedProjects: Project[] = projects.map((p) => {
    // Find queued builds for this project's targets
    const projectQueuedBuilds = queuedBuilds.filter(
      (b) => b.projectRoot === p.root
    );

    return {
      id: p.root,
      name: p.name,
      type: 'project',
      path: p.root,
      builds: p.targets.map((t) => {
        // Check if this target has a queued build
        const queuedBuild = projectQueuedBuilds.find(
          (b) => b.targets?.includes(t.name)
        );

        const status = queuedBuild
          ? queuedBuild.status === 'building'
            ? 'building'
            : 'queued'
          : t.lastBuild?.status === 'failed'
          ? 'error'
          : t.lastBuild?.status || 'idle';

        return {
          id: t.name,
          name: t.name,
          entry: t.entry,
          status: status as BuildTarget['status'],
          errors: t.lastBuild?.errors,
          warnings: t.lastBuild?.warnings,
          duration: t.lastBuild?.elapsedSeconds,
          buildId: queuedBuild?.buildId,
          elapsedSeconds: queuedBuild?.elapsedSeconds,
          currentStage: queuedBuild?.stages?.find((s) => s.status === 'running')?.displayName,
          queuePosition: queuedBuild?.queuePosition,
        };
      }),
      lastBuildStatus: p.targets.some((t) => t.lastBuild?.status === 'failed')
        ? 'failed'
        : p.targets.some((t) => t.lastBuild?.status === 'warning')
        ? 'warning'
        : p.targets.every((t) => t.lastBuild?.status === 'success')
        ? 'success'
        : undefined,
    };
  });

  // Handlers
  const handleSelect = useCallback(
    (newSelection: Selection) => {
      if (newSelection.type === 'project' && newSelection.projectId) {
        selectProject(newSelection.projectId);
      } else if (newSelection.type === 'none') {
        selectProject(null);
      }
    },
    [selectProject]
  );

  const handleBuild = useCallback(
    (level: 'project' | 'build' | 'symbol', id: string, label: string) => {
      if (!selectedProjectRoot) return;

      if (level === 'project') {
        // Build all selected targets or all targets
        const targetsTooBuild =
          selectedTargetNames.length > 0
            ? selectedTargetNames
            : projects
                .find((p) => p.root === selectedProjectRoot)
                ?.targets.map((t) => t.name) || [];
        startBuild(selectedProjectRoot, targetsTooBuild).catch(console.error);
      } else if (level === 'build') {
        // Build specific target
        startBuild(selectedProjectRoot, [id]).catch(console.error);
      }
    },
    [selectedProjectRoot, selectedTargetNames, projects, startBuild]
  );

  const handleCancelBuild = useCallback(
    (buildId: string) => {
      cancelBuild(buildId).catch(console.error);
    },
    [cancelBuild]
  );

  const handleProjectExpand = useCallback(async (projectRoot: string) => {
    // Fetch modules for the expanded project
    try {
      const [modulesRes, filesRes, depsRes] = await Promise.all([
        api.modules.list(projectRoot),
        api.files.list(projectRoot),
        api.dependencies.list(projectRoot),
      ]);
      useStore.getState().setProjectModules(projectRoot, modulesRes.modules);
      useStore.getState().setProjectFiles(projectRoot, filesRes.files);
      useStore.getState().setProjectDependencies(projectRoot, depsRes.dependencies);
    } catch (error) {
      console.error('Failed to fetch project data:', error);
    }
  }, []);

  // Check if targets are selected
  const hasSelectedTargets = selectedTargetNames.length > 0;
  const canBuild = selectedProjectRoot && hasSelectedTargets;

  return (
    <div className="projects-panel-connected">
      {/* Project List */}
      <div className="projects-list">
        {transformedProjects.map((project) => (
          <div
            key={project.id}
            className={`project-item ${
              project.id === selectedProjectRoot ? 'selected' : ''
            }`}
          >
            {/* Project Header */}
            <div
              className="project-header"
              onClick={() => handleSelect({ type: 'project', projectId: project.id })}
            >
              <span className="project-name">{project.name}</span>
              {project.lastBuildStatus && (
                <span className={`status-badge ${project.lastBuildStatus}`}>
                  {project.lastBuildStatus}
                </span>
              )}
            </div>

            {/* Targets */}
            {project.id === selectedProjectRoot && (
              <div className="targets-list">
                {project.builds.map((target) => (
                  <div
                    key={target.id}
                    className={`target-item ${
                      selectedTargetNames.includes(target.name) ? 'selected' : ''
                    }`}
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleTarget(target.name);
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={selectedTargetNames.includes(target.name)}
                      onChange={() => toggleTarget(target.name)}
                      onClick={(e) => e.stopPropagation()}
                    />
                    <span className="target-name">{target.name}</span>
                    <span className={`target-status ${target.status}`}>
                      {target.status}
                    </span>
                    {target.status === 'building' && target.currentStage && (
                      <span className="current-stage">{target.currentStage}</span>
                    )}
                    {target.buildId && target.status !== 'idle' && (
                      <button
                        className="cancel-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCancelBuild(target.buildId!);
                        }}
                        title="Cancel build"
                      >
                        ×
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Build Button */}
      {canBuild && (
        <div className="build-actions">
          <button
            className="build-btn primary"
            onClick={() =>
              handleBuild('project', selectedProjectRoot!, 'Build')
            }
          >
            Build ({selectedTargetNames.length} target
            {selectedTargetNames.length !== 1 ? 's' : ''})
          </button>
        </div>
      )}
    </div>
  );
}
