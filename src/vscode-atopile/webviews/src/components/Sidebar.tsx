/**
 * Main sidebar component with modern card-based design.
 */

import { useEffect, useState } from 'react';
import { useBuildStore } from '../stores/buildStore';
import { ActionButton } from './ActionButton';
import { BuildItem } from './BuildItem';
import './Sidebar.css';

// Get VS Code API
const vscode = acquireVsCodeApi();

export function Sidebar() {
  const [version, setVersion] = useState<string>('');
  const [logoUri, setLogoUri] = useState<string>('');

  const {
    builds,
    actionButtons,
    selectedBuildName,
    selectedStageName,
    isConnected,
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

  const handleSelectBuild = (buildName: string) => {
    setSelectedBuild(buildName);
    vscode.postMessage({ type: 'selectBuild', buildName });
  };

  const handleSelectStage = (buildName: string, stageName: string) => {
    setSelectedBuild(buildName);
    setSelectedStage(stageName);
    vscode.postMessage({ type: 'selectStage', buildName, stageName });
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

      {/* Builds Card */}
      <div className="card card-flex">
        <div className="card-header">
          <span className="card-title">Builds</span>
          {builds.length > 0 && (
            <span className="card-badge">{builds.length}</span>
          )}
        </div>
        <div className="card-content builds-list">
          {builds.length === 0 ? (
            <div className="empty-state">
              {!isConnected ? (
                <>
                  <div className="empty-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <circle cx="12" cy="12" r="10" />
                      <path d="M12 8v4M12 16h.01" />
                    </svg>
                  </div>
                  <span className="empty-title">Not Connected</span>
                  <span className="empty-desc">Run a build to connect</span>
                </>
              ) : (
                <>
                  <div className="empty-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <polygon points="5 3 19 12 5 21 5 3" />
                    </svg>
                  </div>
                  <span className="empty-title">No Builds</span>
                  <span className="empty-desc">Click Build to start</span>
                </>
              )}
            </div>
          ) : (
            builds.map((build) => (
              <BuildItem
                key={build.display_name}
                build={build}
                isSelected={selectedBuildName === build.display_name}
                selectedStageName={selectedBuildName === build.display_name ? selectedStageName : null}
                onSelectBuild={handleSelectBuild}
                onSelectStage={handleSelectStage}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}
