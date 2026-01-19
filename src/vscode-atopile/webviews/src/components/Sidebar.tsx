/**
 * Main sidebar component with modern card-based design.
 */

import { useEffect, useState } from 'react';
import { useBuildStore } from '../stores/buildStore';
import { ActionButton } from './ActionButton';
import { BuildTargetItem } from './BuildTargetItem';
import type { BuildTarget } from '../types/build';
import './Sidebar.css';

// Get VS Code API
const vscode = acquireVsCodeApi();

export function Sidebar() {
  const [version, setVersion] = useState<string>('');
  const [logoUri, setLogoUri] = useState<string>('');

  const {
    // Build targets (from ato.yaml)
    projects,
    selectedProjectRoot,
    selectedTargetNames,
    setProjects,
    setSelectedProjectRoot,
    setSelectedTargetNames,
    // Build runs (from dashboard)
    builds,
    actionButtons,
    selectedBuildName,
    selectedStageName,
    setBuilds,
    setActionButtons,
    setSelectedBuild,
    setSelectedStage,
    setConnected,
  } = useBuildStore();

  // Handle messages from VS Code
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const message = event.data;

      switch (message.type) {
        case 'extensionInfo':
          setVersion(message.data.version || '');
          setLogoUri(message.data.logoUri || '');
          break;

        case 'updateBuildTargets':
          setProjects(message.data.projects || []);
          setSelectedProjectRoot(message.data.selectedProjectRoot);
          setSelectedTargetNames(message.data.selectedTargetNames || []);
          break;

        case 'updateBuilds':
          setBuilds(message.data.builds || []);
          setConnected(message.data.isConnected ?? false);
          break;

        case 'updateActionButtons':
          setActionButtons(message.data.buttons || []);
          break;

        case 'selectBuild':
          setSelectedBuild(message.data.buildName);
          break;

        case 'selectStage':
          setSelectedBuild(message.data.buildName);
          setSelectedStage(message.data.stageName);
          break;
      }
    };

    window.addEventListener('message', handleMessage);
    vscode.postMessage({ type: 'ready' });
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  const handleActionClick = (commandId: string) => {
    vscode.postMessage({ type: 'executeCommand', command: commandId });
  };

  const handleSelectStage = (buildName: string, stageName: string) => {
    setSelectedBuild(buildName);
    setSelectedStage(stageName);
    vscode.postMessage({ type: 'selectStage', buildName, stageName });
  };

  const handleToggleTarget = (targetName: string, projectRoot: string) => {
    vscode.postMessage({ type: 'toggleTarget', targetName, projectRoot });
  };

  const handleBuildProject = () => {
    vscode.postMessage({ type: 'buildProject' });
  };

  const selectedProject = projects.find(p => p.root === selectedProjectRoot);

  // Find build run for a target (match by name)
  const getBuildForTarget = (target: BuildTarget) => {
    return builds.find(b => b.name === target.name);
  };

  return (
    <div className="sidebar">
      {/* Header with logo and version */}
      <div className="sidebar-header">
        {logoUri && <img src={logoUri} alt="atopile" className="sidebar-logo" />}
        <div className="sidebar-header-text">
          <span className="sidebar-title">atopile</span>
          {version && <span className="sidebar-version">v{version}</span>}
        </div>
      </div>

      {/* Actions Card */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Actions</span>
        </div>
        <div className="card-content actions-grid">
          {actionButtons.map((btn) => (
            <ActionButton
              key={btn.id}
              icon={btn.icon}
              label={btn.label}
              tooltip={btn.tooltip}
              onClick={() => handleActionClick(btn.id)}
            />
          ))}
        </div>
      </div>

      {/* Builds Card - Combined targets and status */}
      <div className="card card-flex">
        <div className="card-header">
          <span className="card-title">Builds</span>
          {selectedTargetNames.length > 0 && (
            <span className="card-badge">{selectedTargetNames.length}</span>
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
            </div>
          ) : (
            <>
              {/* Selected project with play button */}
              <div className="project-header">
                <div className="project-info">
                  <svg className="project-icon" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M1.5 2A1.5 1.5 0 0 0 0 3.5v9A1.5 1.5 0 0 0 1.5 14h13a1.5 1.5 0 0 0 1.5-1.5V5.5A1.5 1.5 0 0 0 14.5 4H8.293L6.854 2.561A1.5 1.5 0 0 0 5.793 2H1.5z" />
                  </svg>
                  <span className="project-name">{selectedProject.name}</span>
                </div>
                <button
                  className="build-play-button"
                  onClick={handleBuildProject}
                  disabled={selectedTargetNames.length === 0}
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
                  selectedProject.targets.map((target) => (
                    <BuildTargetItem
                      key={target.name}
                      target={target}
                      build={getBuildForTarget(target)}
                      isChecked={selectedTargetNames.includes(target.name)}
                      isSelected={selectedBuildName === target.name}
                      selectedStageName={selectedBuildName === target.name ? selectedStageName : null}
                      onToggle={() => handleToggleTarget(target.name, target.root)}
                      onSelectStage={(stageName) => handleSelectStage(target.name, stageName)}
                    />
                  ))
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
