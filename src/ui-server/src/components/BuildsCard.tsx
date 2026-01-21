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
  availableModules = []
}: BuildsCardProps) {
  const [expanded, setExpanded] = useState(true); // Default expanded since builds are primary

  const buildingCount = builds.filter(b => b.status === 'building').length;
  const errorCount = builds.filter(b => b.status === 'error').length;
  const successCount = builds.filter(b => b.status === 'success').length;

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
        <span className="builds-count">{builds.length}</span>

        {/* Status indicators */}
        {buildingCount > 0 && (
          <span className="builds-status-badge building" title={`${buildingCount} building`}>
            {buildingCount}
          </span>
        )}
        {errorCount > 0 && (
          <span className="builds-status-badge error" title={`${errorCount} failed`}>
            {errorCount}
          </span>
        )}
        {successCount > 0 && errorCount === 0 && buildingCount === 0 && (
          <span className="builds-status-badge success" title={`${successCount} passed`}>
            {successCount}
          </span>
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
            />
          ))}

          {/* Add new build button */}
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
        </div>
      )}
    </div>
  );
}
