/**
 * BuildsCard - Displays build targets in a collapsible card format.
 * Similar styling to FileExplorer and DependencyCard for consistency.
 */

import { useState } from 'react';
import { Hammer, ChevronDown, Plus } from 'lucide-react';
import { BuildNode } from './BuildNode';
import type { Selection, BuildTarget, ModuleDefinition } from './projectsTypes';
import './BuildsCard.css';

interface BuildsCardProps {
  builds: BuildTarget[];
  projectId: string;
  selection: Selection;
  onSelect: (selection: Selection) => void;
  onBuild: (level: 'project' | 'build' | 'symbol', id: string, label: string) => void;
  onCancelBuild?: (buildId: string) => void;
  onStageFilter?: (stageName: string, buildId?: string, projectId?: string) => void;
  onUpdateBuild?: (projectId: string, buildId: string, updates: Partial<BuildTarget>) => void;
  onDeleteBuild?: (projectId: string, buildId: string) => void;
  onOpenSource?: (projectId: string, entry: string) => void;
  onOpenKiCad?: (projectId: string, buildId: string) => void;
  onOpenLayout?: (projectId: string, buildId: string) => void;
  onOpen3D?: (projectId: string, buildId: string) => void;
  onAddBuild?: (projectId: string) => void;
  availableModules?: ModuleDefinition[];
  // Read-only mode for packages: hides build/delete buttons, status badges, add build
  readOnly?: boolean;
  // Default expanded state (true for local projects, false for packages)
  defaultExpanded?: boolean;
}

export function BuildsCard({
  builds,
  projectId,
  selection,
  onSelect,
  onBuild,
  onCancelBuild,
  onStageFilter,
  onUpdateBuild,
  onDeleteBuild,
  onOpenSource,
  onOpenKiCad,
  onOpenLayout,
  onOpen3D,
  onAddBuild,
  availableModules = [],
  readOnly = false,
  defaultExpanded = true
}: BuildsCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const buildingCount = builds.filter(b => b.status === 'building').length;
  const queuedCount = builds.filter(b => b.status === 'queued').length;
  const errorCount = builds.filter(b => b.status === 'error').length;
  const warningCount = builds.filter(b => b.status === 'warning').length;
  const successCount = builds.filter(b => b.status === 'success').length;
  const idleCount = builds.filter(b => b.status === 'idle').length;

  // Show status breakdown instead of total count (only in non-readOnly mode)
  const hasStatusBadges = !readOnly && (buildingCount > 0 || queuedCount > 0 || errorCount > 0 ||
                          warningCount > 0 || successCount > 0);

  return (
    <div className="builds-card" onClick={(e) => e.stopPropagation()}>
      <div
        className="builds-card-header"
        onClick={(e) => {
          e.stopPropagation();
          setExpanded(!expanded);
        }}
      >
        <span className="builds-card-expand">
          <ChevronDown
            size={12}
            className={`expand-icon ${expanded ? 'expanded' : ''}`}
          />
        </span>
        <Hammer size={14} className="builds-card-icon" />
        <span className="builds-card-title">
          Builds
        </span>

        {/* In readOnly mode, just show count; otherwise show status breakdown */}
        {readOnly ? (
          <span className="builds-count">{builds.length}</span>
        ) : (
          <>
            {/* Status breakdown badges - show each non-zero status */}
            {buildingCount > 0 && (
              <span className="builds-status-badge building" title={`${buildingCount} building`}>
                {buildingCount}
              </span>
            )}
            {queuedCount > 0 && (
              <span className="builds-status-badge queued" title={`${queuedCount} queued`}>
                {queuedCount}
              </span>
            )}
            {errorCount > 0 && (
              <span className="builds-status-badge error" title={`${errorCount} failed`}>
                {errorCount}
              </span>
            )}
            {warningCount > 0 && (
              <span className="builds-status-badge warning" title={`${warningCount} warnings`}>
                {warningCount}
              </span>
            )}
            {successCount > 0 && (
              <span className="builds-status-badge success" title={`${successCount} passed`}>
                {successCount}
              </span>
            )}
            {/* Only show grey count if all builds are idle (no status yet) */}
            {!hasStatusBadges && idleCount > 0 && (
              <span className="builds-count">{idleCount}</span>
            )}
          </>
        )}
      </div>

      {expanded && (
        <div className="builds-card-content">
          {builds.map((build, idx) => (
            <BuildNode
              key={`${build.id}-${idx}`}
              build={build}
              projectId={projectId}
              selection={selection}
              onSelect={onSelect}
              onBuild={onBuild}
              onCancelBuild={onCancelBuild}
              onStageFilter={onStageFilter}
              onUpdateBuild={onUpdateBuild}
              onDeleteBuild={onDeleteBuild}
              onOpenSource={onOpenSource}
              onOpenKiCad={onOpenKiCad}
              onOpenLayout={onOpenLayout}
              onOpen3D={onOpen3D}
              availableModules={availableModules}
              allBuilds={builds}
              readOnly={readOnly}
            />
          ))}

          {/* Add new build button - only in edit mode */}
          {!readOnly && (
            <button
              className="add-build-btn"
              onClick={(e) => {
                e.stopPropagation();
                onAddBuild?.(projectId);
              }}
              title="Add new build target"
            >
              <Plus size={12} />
              <span>Add build</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
