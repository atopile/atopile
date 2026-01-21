/**
 * DependencyCard - Displays project dependencies in a compact card format.
 * Similar styling to BuildQueuePanel but focused on installed packages.
 */

import { useState } from 'react';
import { Package, ChevronDown, RefreshCw, Github } from 'lucide-react';
import './DependencyCard.css';

export interface ProjectDependency {
  identifier: string;  // e.g., "atopile/resistors"
  version: string;     // Installed version
  latestVersion?: string;  // Latest available version
  name: string;        // e.g., "resistors"
  publisher: string;   // e.g., "atopile"
  repository?: string;
  hasUpdate?: boolean;
}

interface DependencyItemProps {
  dependency: ProjectDependency;
  availableVersions?: string[];
  onVersionChange?: (identifier: string, newVersion: string) => void;
  onOpenRepository?: (url: string) => void;
}

function DependencyItem({
  dependency,
  availableVersions = [],
  onVersionChange,
  onOpenRepository
}: DependencyItemProps) {
  const [selectedVersion, setSelectedVersion] = useState(dependency.version);
  const hasUpdate = dependency.hasUpdate ||
    (dependency.latestVersion && dependency.version !== dependency.latestVersion);

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

  return (
    <div className={`dependency-item ${hasUpdate ? 'has-update' : ''}`}>
      <div className="dependency-info">
        <Package size={14} className="dependency-icon" />
        <span className="dependency-name" title={dependency.identifier}>
          {dependency.name}
        </span>
        {dependency.publisher && dependency.publisher !== 'atopile' && (
          <span className="dependency-publisher">by {dependency.publisher}</span>
        )}
      </div>

      <div className="dependency-actions">
        {/* Version selector */}
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

        {/* GitHub link if available */}
        {dependency.repository && (
          <button
            className="dependency-link-btn"
            onClick={(e) => {
              e.stopPropagation();
              onOpenRepository?.(dependency.repository!);
            }}
            title="View on GitHub"
          >
            <Github size={12} />
          </button>
        )}

        {/* Update indicator */}
        {hasUpdate && (
          <span className="dependency-update-badge" title="Update available">
            <RefreshCw size={10} />
          </span>
        )}
      </div>
    </div>
  );
}

interface DependencyCardProps {
  dependencies: ProjectDependency[];
  projectId: string;
  onVersionChange?: (projectId: string, identifier: string, newVersion: string) => void;
  onOpenRepository?: (url: string) => void;
}

export function DependencyCard({
  dependencies,
  projectId,
  onVersionChange,
  onOpenRepository
}: DependencyCardProps) {
  const [expanded, setExpanded] = useState(false);

  if (!dependencies || dependencies.length === 0) {
    return null;
  }

  const updateCount = dependencies.filter(d =>
    d.hasUpdate || (d.latestVersion && d.version !== d.latestVersion)
  ).length;

  return (
    <div className="dependency-card">
      <div
        className="dependency-card-header"
        onClick={() => setExpanded(!expanded)}
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
        {updateCount > 0 && (
          <span className="dependency-update-count" title={`${updateCount} update${updateCount > 1 ? 's' : ''} available`}>
            <RefreshCw size={10} />
            {updateCount}
          </span>
        )}
      </div>

      {expanded && (
        <div className="dependency-card-content">
          {dependencies.map((dep) => (
            <DependencyItem
              key={dep.identifier}
              dependency={dep}
              onVersionChange={(id, v) => onVersionChange?.(projectId, id, v)}
              onOpenRepository={onOpenRepository}
            />
          ))}
        </div>
      )}
    </div>
  );
}
