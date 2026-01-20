/**
 * Sidebar component - STATELESS.
 * Receives AppState from extension, sends actions back.
 */

import { useEffect, useState } from 'react';
import type { AppState } from '../types/build';
import { ActionButton } from './ActionButton';
import { BuildTargetItem } from './BuildTargetItem';
import './Sidebar.css';

const vscode = acquireVsCodeApi();

// Send action to extension
const action = (name: string, data?: object) => {
  vscode.postMessage({ type: 'action', action: name, ...data });
};

// Static action buttons
const ACTION_BUTTONS = [
  { id: 'atopile.build', label: 'Build All', icon: 'play', tooltip: 'Build all selected targets' },
];

export function Sidebar() {
  // Single piece of state: AppState from extension
  const [state, setState] = useState<AppState | null>(null);

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const msg = event.data;
      if (msg.type === 'state') {
        setState(msg.data);
      }
    };
    window.addEventListener('message', handleMessage);
    vscode.postMessage({ type: 'ready' });
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  if (!state) {
    return <div className="sidebar loading">Loading...</div>;
  }

  const selectedProject = state.projects.find(p => p.root === state.selectedProjectRoot);

  return (
    <div className="sidebar">
      {/* Header with logo and version */}
      <div className="sidebar-header">
        {state.logoUri && <img src={state.logoUri} alt="atopile" className="sidebar-logo" />}
        <div className="sidebar-header-text">
          <span className="sidebar-title">atopile</span>
          {state.version && <span className="sidebar-version">v{state.version}</span>}
        </div>
      </div>

      {/* Actions Card */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Actions</span>
        </div>
        <div className="card-content actions-grid">
          {ACTION_BUTTONS.map((btn) => (
            <ActionButton
              key={btn.id}
              icon={btn.icon}
              label={btn.label}
              tooltip={btn.tooltip}
              onClick={() => action('executeCommand', { command: btn.id })}
            />
          ))}
        </div>
      </div>

      {/* Builds Card */}
      <div className="card card-flex">
        <div className="card-header">
          <span className="card-title">Builds</span>
          {state.selectedTargetNames.length > 0 && (
            <span className="card-badge">{state.selectedTargetNames.length}</span>
          )}
        </div>
        <div className="card-content builds-targets">
          {!selectedProject ? (
            <div className="empty-state">
              <div className="empty-icon">
                <svg viewBox="0 0 16 16" fill="currentColor">
                  <path d="M1.5 2A1.5 1.5 0 0 0 0 3.5v9A1.5 1.5 0 0 0 1.5 14h13a1.5 1.5 0 0 0 1.5-1.5V5.5A1.5 1.5 0 0 0 14.5 4H8.293L6.854 2.561A1.5 1.5 0 0 0 5.793 2H1.5z" />
                </svg>
              </div>
              <span className="empty-title">No Project</span>
              <span className="empty-desc">Select a project folder</span>
              <button
                className="select-project-btn"
                onClick={() => action('showProjectPicker')}
              >
                Select Project
              </button>
            </div>
          ) : (
            <>
              {/* Selected project with play button */}
              <div className="project-header">
                <button
                  className="project-selector"
                  onClick={() => action('showProjectPicker')}
                  title="Change project"
                >
                  <svg className="project-icon" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M1.5 2A1.5 1.5 0 0 0 0 3.5v9A1.5 1.5 0 0 0 1.5 14h13a1.5 1.5 0 0 0 1.5-1.5V5.5A1.5 1.5 0 0 0 14.5 4H8.293L6.854 2.561A1.5 1.5 0 0 0 5.793 2H1.5z" />
                  </svg>
                  <span className="project-name">{selectedProject.name}</span>
                  <svg className="project-chevron" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M4.5 5.5L8 9l3.5-3.5" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
                <button
                  className="build-play-button"
                  onClick={() => action('build')}
                  disabled={state.selectedTargetNames.length === 0}
                  title="Build selected targets"
                >
                  <svg viewBox="0 0 16 16" fill="currentColor">
                    <path d="M4 2l10 6-10 6V2z" />
                  </svg>
                </button>
              </div>

              {/* Build targets with status */}
              <div className="build-targets-list">
                {selectedProject.targets.length === 0 ? (
                  <div className="empty-state-small">
                    <span className="empty-desc">No build targets in ato.yaml</span>
                  </div>
                ) : (
                  selectedProject.targets.map((target) => {
                    const build = state.builds.find(b => b.name === target.name);
                    const isSelected = state.selectedBuildName === build?.display_name;
                    return (
                      <BuildTargetItem
                        key={target.name}
                        target={target}
                        build={build}
                        isChecked={state.selectedTargetNames.includes(target.name)}
                        isSelected={isSelected}
                        isExpanded={state.expandedTargets.includes(target.name)}
                        onToggle={() => action('toggleTarget', { name: target.name })}
                        onToggleExpand={() => action('toggleTargetExpanded', { name: target.name })}
                        onSelect={() => {
                          if (build?.display_name) {
                            action('selectBuild', { buildName: build.display_name });
                          }
                        }}
                        onBuild={() => action('buildTarget', { name: target.name })}
                        onOpenPcb={() => action('openPcbForTarget', { name: target.name })}
                      />
                    );
                  })
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
