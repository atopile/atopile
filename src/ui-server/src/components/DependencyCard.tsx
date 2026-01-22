/**
 * DependencyCard - Displays project dependencies in a compact card format.
 * Similar styling to BuildQueuePanel but focused on installed packages.
 */

import { useState } from 'react';
import { Package, ChevronDown, X, Loader2 } from 'lucide-react';
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
  onRemove?: (identifier: string) => void;
  readOnly?: boolean;
}

function DependencyItem({
  dependency,
  availableVersions = [],
  onVersionChange,
  onRemove,
  readOnly = false
}: DependencyItemProps) {
  const [selectedVersion, setSelectedVersion] = useState(dependency.version);
  const [isRemoving, setIsRemoving] = useState(false);
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
  );
}

interface DependencyCardProps {
  dependencies: ProjectDependency[];
  projectId: string;
  onVersionChange?: (projectId: string, identifier: string, newVersion: string) => void;
  onRemove?: (projectId: string, identifier: string) => void;
  // Read-only mode for packages: hides version selector and remove button
  readOnly?: boolean;
}

export function DependencyCard({
  dependencies,
  projectId,
  onVersionChange,
  onRemove,
  readOnly = false
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
              onVersionChange={(id, v) => onVersionChange?.(projectId, id, v)}
              onRemove={(id) => onRemove?.(projectId, id)}
              readOnly={readOnly}
            />
          ))}
        </div>
      )}
    </div>
  );
}
