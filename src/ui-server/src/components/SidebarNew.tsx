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
import { useStore } from '../store';
import { CollapsibleSection } from './CollapsibleSection';
import { ProjectsPanelConnected } from './ProjectsPanelConnected';
import { ProblemsPanelConnected } from './ProblemsPanelConnected';
import { BuildQueuePanelConnected } from './BuildQueuePanelConnected';
import './Sidebar.css';
import '../styles.css';

// Default logo as PNG data URI (from existing Sidebar)
const DEFAULT_LOGO = `data:image/png;base64,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`;

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

  // Get version and logo from store
  const version = useStore((state) => state.version);
  const logoUri = useStore((state) => state.logoUri) || DEFAULT_LOGO;

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
        <div className="sidebar-logo-row">
          <img src={logoUri} alt="atopile" className="sidebar-logo" />
          <span className="sidebar-title">atopile</span>
        </div>
        <div className="sidebar-header-right">
          <span className="sidebar-version">{version}</span>
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
