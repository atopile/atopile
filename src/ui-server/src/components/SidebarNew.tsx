/**
 * SidebarNew - Sidebar using the new store-based architecture.
 *
 * This component demonstrates the new pattern:
 * - Uses hooks (useProjects, useBuilds, etc.) instead of props
 * - State comes from Zustand store (connected to backend via WebSocket)
 * - Actions are dispatched through hooks
 * - Uses Connected components that get state from hooks internally
 *
 * This can coexist with the existing Sidebar.tsx during migration.
 */

import { useState } from 'react';
import { Settings, AlertCircle } from 'lucide-react';
import { useProjects, useBuilds, useProblems, useConnection } from '../hooks';
import { CollapsibleSection } from './CollapsibleSection';
import { ProjectsPanelConnected } from './ProjectsPanelConnected';
import { ProblemsPanelConnected } from './ProblemsPanelConnected';
import { BuildQueuePanelConnected } from './BuildQueuePanelConnected';
import './Sidebar.css';
import '../styles.css';

export function SidebarNew() {
  // Hooks for state and actions - Connected components use hooks internally
  const { projects } = useProjects();
  const { queuedBuilds } = useBuilds();
  const { errorCount, warningCount } = useProblems();
  const { isConnected } = useConnection();
  const buildQueueItemHeight = 34;
  const buildQueueMinHeight = 40;
  const buildQueuePadding = 12;
  const buildQueueDesiredHeight = Math.max(
    buildQueueMinHeight,
    Math.max(1, queuedBuilds.length) * buildQueueItemHeight + buildQueuePadding
  );
  const buildQueueMaxHeight = Math.min(240, buildQueueDesiredHeight);

  const extensionVersion =
    typeof window !== 'undefined'
      ? (window as Window & { __ATOPILE_EXTENSION_VERSION__?: string })
          .__ATOPILE_EXTENSION_VERSION__
      : undefined;

  // Local UI state for section collapse
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(
    new Set(['buildQueue', 'packages', 'problems', 'stdlib', 'variables', 'bom'])
  );

  // Toggle section collapse
  const toggleSection = (section: string) => {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  return (
    <div className="sidebar">
      {/* Header */}
      <div className="sidebar-header">
        <span className="sidebar-title">atopile</span>
        <div className="sidebar-header-right">
          {extensionVersion && <span className="sidebar-version">{extensionVersion}</span>}
          <button className="icon-button" title="Settings">
            <Settings size={16} />
          </button>
        </div>
      </div>

      {/* Connection indicator */}
      {!isConnected && (
        <div className="connection-warning">
          <AlertCircle size={14} />
          <span>Connecting to backend...</span>
        </div>
      )}

      {/* Scrollable content */}
      <div className="sidebar-content">
        {/* Projects Section - Uses connected component with hooks */}
        <CollapsibleSection
          id="projects"
          title="Projects"
          collapsed={collapsedSections.has('projects')}
          onToggle={() => toggleSection('projects')}
          badge={projects.length > 0 ? projects.length : undefined}
        >
          <ProjectsPanelConnected />
        </CollapsibleSection>

        {/* Build Queue Section - Uses connected component with hooks */}
        <CollapsibleSection
          id="buildQueue"
          title="Build Queue"
          collapsed={collapsedSections.has('buildQueue')}
          onToggle={() => toggleSection('buildQueue')}
          badge={queuedBuilds.length > 0 ? queuedBuilds.length : undefined}
          maxHeight={buildQueueMaxHeight}
        >
          <BuildQueuePanelConnected />
        </CollapsibleSection>

        {/* Problems Section - Uses connected component with hooks */}
        <CollapsibleSection
          id="problems"
          title="Problems"
          collapsed={collapsedSections.has('problems')}
          onToggle={() => toggleSection('problems')}
          badge={
            errorCount + warningCount > 0
              ? `${errorCount}E ${warningCount}W`
              : undefined
          }
        >
          <ProblemsPanelConnected />
        </CollapsibleSection>
      </div>
    </div>
  );
}
