/**
 * DependencyCard - Displays project dependencies in a compact card format.
 * Dependencies can be expanded to show their content using ProjectCard.
 *
 * See COMPONENT_ARCHITECTURE.md for the editability matrix.
 */

import { useState, useEffect } from 'react'
import { Package, ChevronDown, ChevronRight, X, Loader2 } from 'lucide-react'
import { ProjectCard } from './ProjectCard'
import { sendActionWithResponse } from '../api/websocket'
import { compareVersionsDesc } from '../utils/packageUtils'
import type { FileTreeNode } from './FileExplorer'
import type { BuildTarget as ProjectBuildTarget } from '../types/build'
import type { Project, Selection } from './projectsTypes'
import './DependencyCard.css'

export interface ProjectDependency {
  identifier: string;  // e.g., "atopile/resistors"
  version: string;     // Installed version
  latestVersion?: string;  // Latest available version
  name: string;        // e.g., "resistors"
  publisher: string;   // e.g., "atopile"
  repository?: string;
  hasUpdate?: boolean;
  isDirect?: boolean;
  via?: string[];
  installedPath?: string;  // Absolute path where dependency is installed
  summary?: string;  // Package summary/description from ato.yaml
  usageContent?: string;  // Content of usage.ato if it exists
  license?: string;  // License from ato.yaml package section
  homepage?: string;  // Homepage URL from ato.yaml package section
}

// Convert a ProjectDependency to a Project for use with ProjectCard
// Uses installedPath from backend if available, otherwise falls back to identifier
function dependencyToProject(dependency: ProjectDependency): Project {
  // Use the actual installed path from the backend
  // If not installed (installedPath is null), fall back to identifier
  const root = dependency.installedPath || dependency.identifier;

  return {
    id: dependency.identifier,
    name: dependency.name,
    type: 'package',
    root,
    version: dependency.version,
    latestVersion: dependency.latestVersion,
    publisher: dependency.publisher,
    repository: dependency.repository,
    summary: dependency.summary,
    usageContent: dependency.usageContent,
    license: dependency.license,
    homepage: dependency.homepage,
    builds: [],  // Will be fetched via fetchBuilds when expanded
  };
}

interface DependencyItemProps {
  dependency: ProjectDependency;
  projectFilesByRoot?: Record<string, FileTreeNode[]>;
  projectBuildsByRoot?: Record<string, ProjectBuildTarget[]>;  // Builds for installed dependencies
  availableVersions?: string[];
  onVersionChange?: (identifier: string, newVersion: string) => void;
  onRemove?: (identifier: string) => void;
  onProjectExpand?: (projectRoot: string) => void;
  onFileClick?: (projectId: string, filePath: string) => void;
  readOnly?: boolean;
  allowExpand?: boolean;
  isUpdating?: boolean;  // True when this dependency is being updated/installed
}

function DependencyItem({
  dependency,
  projectFilesByRoot,
  projectBuildsByRoot = {},
  availableVersions = [],
  onVersionChange,
  onRemove,
  onProjectExpand,
  onFileClick,
  readOnly = false,
  allowExpand = true,
  isUpdating = false
}: DependencyItemProps) {
  const [selectedVersion, setSelectedVersion] = useState(dependency.version);
  const [isRemoving, setIsRemoving] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const isDirect = dependency.isDirect !== false;
  const canEdit = !readOnly && isDirect;
  const hasUpdate = canEdit &&
    !!dependency.latestVersion &&
    dependency.version !== dependency.latestVersion;
  // Check if the dependency is up-to-date (installed version matches latest or no latest known)
  const isUpToDate = !hasUpdate && (!dependency.latestVersion || dependency.version === dependency.latestVersion);
  const viaLabel = !isDirect && dependency.via && dependency.via.length > 0
    ? dependency.via.map((id) => id.split('/').pop() || id).join(', ')
    : null;

  // Build versions list
  const versions = availableVersions.length > 0
    ? availableVersions
    : dependency.latestVersion && dependency.latestVersion !== dependency.version
      ? [dependency.latestVersion, dependency.version]
      : [dependency.version];

  const handleVersionChange = (newVersion: string) => {
    setSelectedVersion(newVersion);
    onVersionChange?.(dependency.identifier, newVersion);
  };

  // Convert dependency to Project for ProjectCard
  const dependencyAsProject = dependencyToProject(dependency);

  const handleClick = (e: React.MouseEvent) => {
    if (allowExpand) {
      e.stopPropagation();
      const nextExpanded = !isExpanded;
      setIsExpanded(nextExpanded);
      if (nextExpanded) {
        onProjectExpand?.(dependencyAsProject.root);
      }
    }
  };

  // Dummy handlers for ProjectCard (read-only mode)
  const noopSelection: Selection = { type: 'none' };
  const noopSelect = () => {};
  const noopBuild = () => {};

  return (
    <div className={`dependency-item-container ${isExpanded ? 'expanded' : ''}`}>
      <div
        className={`dependency-item ${!isDirect ? 'transitive' : ''} ${hasUpdate ? 'has-update' : ''} ${isUpToDate && canEdit ? 'up-to-date' : ''} ${allowExpand ? 'expandable' : ''}`}
        onClick={handleClick}
      >
        <div className="dependency-info">
          {allowExpand && (
            <span className="dependency-expand-icon">
              {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            </span>
          )}
          <Package size={14} className="dependency-icon" />
          <span className="dependency-name" title={dependency.identifier}>
            {dependency.name}
          </span>
          {dependency.publisher && dependency.publisher !== 'atopile' && (
            <span className="dependency-publisher">by {dependency.publisher}</span>
          )}
          {!isDirect && viaLabel && (
            <span
              className="dependency-via"
              title={`via ${dependency.via?.join(', ')}`}
            >
              via {viaLabel}
            </span>
          )}
        </div>

        <div className="dependency-actions">
          {/* Version display/selector */}
          {!canEdit ? (
            <span
              className={`dependency-version-display ${!isDirect ? 'transitive' : ''}`}
              title={isDirect ? `Version ${dependency.version}` : 'Transitive dependency'}
            >
              {dependency.version}
            </span>
          ) : isUpdating ? (
            <span className="dependency-version-updating" title="Updating...">
              <Loader2 size={12} className="spin" />
              <span>{selectedVersion}</span>
            </span>
          ) : (
            <select
              className={`dependency-version-select ${hasUpdate ? 'update-available' : ''} ${isUpToDate ? 'up-to-date' : ''}`}
              value={selectedVersion}
              onChange={(e) => {
                e.stopPropagation();
                handleVersionChange(e.target.value);
              }}
              onClick={(e) => e.stopPropagation()}
              title={hasUpdate ? `Update available: ${dependency.latestVersion}` : `Version ${dependency.version}`}
              disabled={isUpdating}
            >
              {versions.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          )}

          {/* Remove button - only in edit mode */}
          {canEdit && (
            <button
              className={`dependency-remove-btn ${isRemoving ? 'removing' : ''}`}
              onClick={(e) => {
                e.stopPropagation();
                if (!isRemoving) {
                  setIsRemoving(true);
                  onRemove?.(dependency.identifier);
                }
              }}
              disabled={isRemoving}
              title={isRemoving ? 'Removing...' : `Remove ${dependency.name}`}
            >
              {isRemoving ? <Loader2 size={12} className="spin" /> : <X size={12} />}
            </button>
          )}
        </div>
      </div>

      {/* Expanded content using ProjectCard */}
      {isExpanded && allowExpand && (
        <div className="dependency-expanded-wrapper">
          <ProjectCard
            project={dependencyAsProject}
            preset="dependencyExpanded"
            selection={noopSelection}
            onSelect={noopSelect}
            onBuild={noopBuild}
            isExpanded={true}
            onExpandChange={() => {}}
            projectFiles={projectFilesByRoot?.[dependencyAsProject.root] || []}
            projectBuildsByRoot={projectBuildsByRoot}
            onFileClick={onFileClick ? (_projectId, filePath) => onFileClick(dependencyAsProject.root, filePath) : undefined}
          />
        </div>
      )}
    </div>
  );
}

interface DependencyCardProps {
  dependencies: ProjectDependency[];
  projectId: string;
  projectFilesByRoot?: Record<string, FileTreeNode[]>;
  projectBuildsByRoot?: Record<string, ProjectBuildTarget[]>;  // Builds for installed dependencies
  onVersionChange?: (projectId: string, identifier: string, newVersion: string) => void;
  onRemove?: (projectId: string, identifier: string) => void;
  // Read-only mode for packages: hides version selector and remove button
  readOnly?: boolean;
  // Whether to allow expanding dependencies to show their content
  allowExpand?: boolean;
  onProjectExpand?: (projectRoot: string) => void;
  onFileClick?: (projectId: string, filePath: string) => void;
  // IDs of dependencies currently being updated (format: projectId:dependencyId)
  updatingDependencyIds?: string[];
}

export function DependencyCard({
  dependencies,
  projectId,
  projectFilesByRoot,
  projectBuildsByRoot = {},
  onVersionChange,
  onRemove,
  readOnly = false,
  allowExpand = true,
  onProjectExpand,
  onFileClick,
  updatingDependencyIds = []
}: DependencyCardProps) {
  const [expanded, setExpanded] = useState(false);
  // Store fetched versions for each dependency identifier
  const [dependencyVersions, setDependencyVersions] = useState<Record<string, string[]>>({});
  const [loadingVersions, setLoadingVersions] = useState<Set<string>>(new Set());
  const directDeps = dependencies.filter(dep => dep.isDirect !== false);
  const transitiveDeps = dependencies.filter(dep => dep.isDirect === false);

  // Fetch available versions for all dependencies when card expands
  // Use sequential fetching to avoid overwhelming the server
  useEffect(() => {
    if (!expanded || readOnly) return;

    // Find deps that need fetching
    const depsToFetch = directDeps.filter(
      dep => !dependencyVersions[dep.identifier] && !loadingVersions.has(dep.identifier)
    );

    if (depsToFetch.length === 0) return;

    // Fetch versions sequentially with a small delay between requests
    const fetchSequentially = async () => {
      for (const dep of depsToFetch) {
        // Check again in case state changed
        if (dependencyVersions[dep.identifier]) continue;

        setLoadingVersions(prev => new Set(prev).add(dep.identifier));

        try {
          const response = await sendActionWithResponse('getPackageDetails', { packageId: dep.identifier });
          const result = response.result ?? {};
          const details = (result as { details?: { versions?: { version: string }[] } }).details;

          if (details?.versions && details.versions.length > 0) {
            const versions = details.versions
              .map(v => v.version)
              .filter(v => v && v !== 'unknown')
              .sort(compareVersionsDesc);

            setDependencyVersions(prev => ({
              ...prev,
              [dep.identifier]: versions
            }));
          }
        } catch (error) {
          console.error(`Failed to fetch versions for ${dep.identifier}:`, error);
        } finally {
          setLoadingVersions(prev => {
            const next = new Set(prev);
            next.delete(dep.identifier);
            return next;
          });
        }

        // Small delay between requests to avoid overwhelming the server
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    };

    fetchSequentially();
  }, [expanded, directDeps, readOnly, dependencyVersions, loadingVersions]);

  if (!dependencies || dependencies.length === 0) {
    return null;
  }

  return (
    <div className="dependency-card" onClick={(e) => e.stopPropagation()}>
      <div
        className="dependency-card-header"
        onClick={(e) => {
          e.stopPropagation();
          setExpanded(!expanded);
        }}
      >
        <span className="dependency-card-expand">
          <ChevronDown
            size={12}
            className={`expand-icon ${expanded ? 'expanded' : ''}`}
          />
        </span>
        <Package size={14} className="dependency-card-icon" />
        <span className="dependency-card-title">
          Dependencies
        </span>
        <span className="dependency-count">{dependencies.length}</span>
      </div>

      {expanded && (
        <div className="dependency-card-content">
          {directDeps.map((dep) => {
            // Check if this dependency is currently being updated
            // The key format is projectId:dependencyId (must match handler which receives projectId)
            const isUpdating = updatingDependencyIds.includes(`${projectId}:${dep.identifier}`);
            // Get fetched versions for this dependency (if available)
            const fetchedVersions = dependencyVersions[dep.identifier] || [];
            return (
              <DependencyItem
                key={dep.identifier}
                dependency={dep}
                projectFilesByRoot={projectFilesByRoot}
                projectBuildsByRoot={projectBuildsByRoot}
                availableVersions={fetchedVersions}
                onVersionChange={(id, v) => onVersionChange?.(projectId, id, v)}
                onRemove={(id) => onRemove?.(projectId, id)}
                readOnly={readOnly}
                allowExpand={allowExpand}
                onProjectExpand={onProjectExpand}
                onFileClick={onFileClick}
                isUpdating={isUpdating}
              />
            );
          })}

          {transitiveDeps.length > 0 && (
            <>
              <div className="dependency-section-header">
                <span className="dependency-section-title">Transitive</span>
                <span className="dependency-section-count">{transitiveDeps.length}</span>
              </div>
              {transitiveDeps.map((dep) => (
                <DependencyItem
                  key={dep.identifier}
                  dependency={dep}
                  projectFilesByRoot={projectFilesByRoot}
                  projectBuildsByRoot={projectBuildsByRoot}
                  readOnly={true}
                  allowExpand={allowExpand}
                  onProjectExpand={onProjectExpand}
                  onFileClick={onFileClick}
                  isUpdating={false}
                />
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
