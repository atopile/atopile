/**
 * DependencyCard - Displays project dependencies in a compact card format.
 * Dependencies can be expanded to show their content using ProjectCard.
 *
 * See COMPONENT_ARCHITECTURE.md for the editability matrix.
 */

import { useState } from 'react'
import { Package, ChevronDown, ChevronRight, X, Loader2 } from 'lucide-react'
import { ProjectCard } from './ProjectCard'
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
}

// Convert a ProjectDependency to a Project for use with ProjectCard
// parentProjectRoot is used to compute the actual filesystem path for installed dependencies
function dependencyToProject(dependency: ProjectDependency, parentProjectRoot?: string): Project {
  // Dependencies are installed at <parent_root>/.ato/modules/<package_id>/
  const root = parentProjectRoot
    ? `${parentProjectRoot}/.ato/modules/${dependency.identifier}`
    : dependency.identifier;

  return {
    id: dependency.identifier,
    name: dependency.name,
    type: 'package',
    root,
    version: dependency.version,
    latestVersion: dependency.latestVersion,
    publisher: dependency.publisher,
    repository: dependency.repository,
    builds: [],  // Will be fetched by ProjectCard
  };
}

interface DependencyItemProps {
  dependency: ProjectDependency;
  parentProjectRoot?: string;  // Root path of parent project (for computing dependency path)
  availableVersions?: string[];
  onVersionChange?: (identifier: string, newVersion: string) => void;
  onRemove?: (identifier: string) => void;
  readOnly?: boolean;
  allowExpand?: boolean;
}

function DependencyItem({
  dependency,
  parentProjectRoot,
  availableVersions = [],
  onVersionChange,
  onRemove,
  readOnly = false,
  allowExpand = true
}: DependencyItemProps) {
  const [selectedVersion, setSelectedVersion] = useState(dependency.version);
  const [isRemoving, setIsRemoving] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const hasUpdate = !readOnly && (dependency.hasUpdate ||
    (dependency.latestVersion && dependency.version !== dependency.latestVersion));

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

  const handleClick = (e: React.MouseEvent) => {
    if (allowExpand) {
      e.stopPropagation();
      setIsExpanded(!isExpanded);
    }
  };

  // Convert dependency to Project for ProjectCard
  const dependencyAsProject = dependencyToProject(dependency, parentProjectRoot);

  // Dummy handlers for ProjectCard (read-only mode)
  const noopSelection: Selection = { type: 'none' };
  const noopSelect = () => {};
  const noopBuild = () => {};

  return (
    <div className={`dependency-item-container ${isExpanded ? 'expanded' : ''}`}>
      <div
        className={`dependency-item ${hasUpdate ? 'has-update' : ''} ${allowExpand ? 'expandable' : ''}`}
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
        </div>

        <div className="dependency-actions">
          {/* Version display/selector */}
          {readOnly ? (
            <span className="dependency-version-display" title={`Version ${dependency.version}`}>
              {dependency.version}
            </span>
          ) : (
            <select
              className={`dependency-version-select ${hasUpdate ? 'update-available' : ''}`}
              value={selectedVersion}
              onChange={(e) => {
                e.stopPropagation();
                handleVersionChange(e.target.value);
              }}
              onClick={(e) => e.stopPropagation()}
              title={hasUpdate ? `Update available: ${dependency.latestVersion}` : `Version ${dependency.version}`}
            >
              {versions.map((v, idx) => (
                <option key={v} value={v}>
                  {v}{idx === 0 && hasUpdate && v === dependency.latestVersion ? ' (latest)' : ''}
                </option>
              ))}
            </select>
          )}

          {/* Remove button - only in edit mode */}
          {!readOnly && (
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
          />
        </div>
      )}
    </div>
  );
}

interface DependencyCardProps {
  dependencies: ProjectDependency[];
  projectId: string;
  projectRoot?: string;  // Root path of project (for computing dependency paths)
  onVersionChange?: (projectId: string, identifier: string, newVersion: string) => void;
  onRemove?: (projectId: string, identifier: string) => void;
  // Read-only mode for packages: hides version selector and remove button
  readOnly?: boolean;
  // Whether to allow expanding dependencies to show their content
  allowExpand?: boolean;
}

export function DependencyCard({
  dependencies,
  projectId,
  projectRoot,
  onVersionChange,
  onRemove,
  readOnly = false,
  allowExpand = true
}: DependencyCardProps) {
  const [expanded, setExpanded] = useState(false);

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
          {dependencies.map((dep) => (
            <DependencyItem
              key={dep.identifier}
              dependency={dep}
              parentProjectRoot={projectRoot}
              onVersionChange={(id, v) => onVersionChange?.(projectId, id, v)}
              onRemove={(id) => onRemove?.(projectId, id)}
              readOnly={readOnly}
              allowExpand={allowExpand}
            />
          ))}
        </div>
      )}
    </div>
  );
}
