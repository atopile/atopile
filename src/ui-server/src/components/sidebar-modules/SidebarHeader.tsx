/**
 * SidebarHeader component - Header with logo, version, and settings dropdown.
 */

import { useEffect, useRef, useState } from 'react';
import { Settings, ChevronDown, FolderOpen, Loader2, AlertCircle, Check, GitBranch, Package, Search } from 'lucide-react';
import { sendAction } from '../../api/websocket';
import { DEFAULT_LOGO } from './sidebarUtils';

// Send action to backend via WebSocket
const action = (name: string, data?: Record<string, unknown>) => {
  if (name === 'openUrl' && data && 'url' in data) {
    const url = (data as { url?: string }).url;
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer');
      return;
    }
  }
  sendAction(name, data);
};

interface AtopileState {
  isInstalling?: boolean;
  installProgress?: {
    message?: string;
    percent?: number;
  } | null;
  error?: string | null;
  source?: 'release' | 'branch' | 'local';
  currentVersion?: string;
  availableVersions?: string[];
  branch?: string | null;
  availableBranches?: string[];
  localPath?: string | null;
  detectedInstallations?: Array<{
    path: string;
    source: string;
    version?: string | null;
  }>;
}

interface SidebarHeaderProps {
  logoUri?: string;
  version?: string;
  atopile?: AtopileState;
  developerMode?: boolean;
}

export function SidebarHeader({ logoUri, version, atopile, developerMode }: SidebarHeaderProps) {
  // Settings dropdown state
  const [showSettings, setShowSettings] = useState(false);
  const settingsRef = useRef<HTMLDivElement>(null);

  // Max concurrent builds setting
  const detectedCores = typeof navigator !== 'undefined' ? navigator.hardwareConcurrency || 4 : 4;
  const [maxConcurrentUseDefault, setMaxConcurrentUseDefault] = useState(true);
  const [maxConcurrentValue, setMaxConcurrentValue] = useState(detectedCores);
  const [defaultMaxConcurrent, setDefaultMaxConcurrent] = useState(detectedCores);

  // Branch search state
  const [branchSearchQuery, setBranchSearchQuery] = useState('');
  const [showBranchDropdown, setShowBranchDropdown] = useState(false);
  const branchDropdownRef = useRef<HTMLDivElement>(null);

  // Close settings dropdown when clicking outside
  useEffect(() => {
    if (!showSettings) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) {
        setShowSettings(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showSettings]);

  // Fetch max concurrent setting when settings open
  useEffect(() => {
    if (showSettings) {
      action('getMaxConcurrentSetting');
    }
  }, [showSettings]);

  // Close branch dropdown when clicking outside
  useEffect(() => {
    if (!showBranchDropdown) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (branchDropdownRef.current && !branchDropdownRef.current.contains(e.target as Node)) {
        setShowBranchDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showBranchDropdown]);

  // Handle action_result events for settings
  useEffect(() => {
    const handleActionResult = (event: Event) => {
      const detail = (event as CustomEvent).detail as {
        action?: string;
        setting?: {
          use_default: boolean;
          custom_value?: number;
          default_value: number;
        };
      };

      if (detail?.setting) {
        setMaxConcurrentUseDefault(detail.setting.use_default);
        setMaxConcurrentValue(detail.setting.custom_value || detail.setting.default_value);
        setDefaultMaxConcurrent(detail.setting.default_value);
      }
    };
    window.addEventListener('atopile:action_result', handleActionResult);
    return () => window.removeEventListener('atopile:action_result', handleActionResult);
  }, []);

  return (
    <div className="panel-header">
      <div className="header-title">
        <img
          className="logo"
          src={logoUri || DEFAULT_LOGO}
          alt="atopile"
        />
        <span>atopile</span>
        {version && <span className="version-badge">v{version}</span>}
      </div>
      <div className="header-actions">
        <div className="settings-dropdown-container" ref={settingsRef}>
          <button
            className={`icon-btn${showSettings ? ' active' : ''}`}
            onClick={() => setShowSettings(!showSettings)}
            title="Settings"
          >
            <Settings size={14} />
          </button>
          {showSettings && (
            <div className="settings-dropdown">
              {/* Installation Progress */}
              {atopile?.isInstalling && (
                <div className="install-progress">
                  <div className="install-progress-header">
                    <Loader2 size={12} className="spinner" />
                    <span>{atopile.installProgress?.message || 'Installing...'}</span>
                  </div>
                  {atopile.installProgress?.percent !== undefined && (
                    <div className="install-progress-bar">
                      <div
                        className="install-progress-fill"
                        style={{ width: `${atopile.installProgress.percent}%` }}
                      />
                    </div>
                  )}
                </div>
              )}

              {/* Error Display */}
              {atopile?.error && (
                <div className="settings-error">
                  <AlertCircle size={12} />
                  <span>{atopile.error}</span>
                </div>
              )}

              {/* Source Type Selector */}
              <div className="settings-group">
                <label className="settings-label">
                  <span className="settings-label-title">Source</span>
                </label>
                <div className="settings-source-buttons">
                  <button
                    className={`source-btn${atopile?.source === 'release' ? ' active' : ''}`}
                    onClick={() => action('setAtopileSource', { source: 'release' })}
                    disabled={atopile?.isInstalling}
                    title="Use a released version from PyPI"
                  >
                    <Package size={12} />
                    Release
                  </button>
                  <button
                    className={`source-btn${atopile?.source === 'branch' ? ' active' : ''}`}
                    onClick={() => action('setAtopileSource', { source: 'branch' })}
                    disabled={atopile?.isInstalling}
                    title="Use a git branch from GitHub"
                  >
                    <GitBranch size={12} />
                    Branch
                  </button>
                  <button
                    className={`source-btn${atopile?.source === 'local' ? ' active' : ''}`}
                    onClick={() => action('setAtopileSource', { source: 'local' })}
                    disabled={atopile?.isInstalling}
                    title="Use a local installation"
                  >
                    <FolderOpen size={12} />
                    Local
                  </button>
                </div>
              </div>

              {/* Version Selector (when using release) */}
              {atopile?.source === 'release' && (
                <div className="settings-group">
                  <label className="settings-label">
                    <span className="settings-label-title">Version</span>
                  </label>
                  <div className="settings-select-wrapper">
                    <select
                      className="settings-select"
                      value={atopile?.currentVersion || ''}
                      onChange={(e) => {
                        action('setAtopileVersion', { version: e.target.value });
                      }}
                      disabled={atopile?.isInstalling}
                    >
                      {(atopile?.availableVersions || []).map((v) => (
                        <option key={v} value={v}>
                          {v}{v === atopile?.availableVersions?.[0] ? ' (latest)' : ''}
                        </option>
                      ))}
                    </select>
                    <ChevronDown size={12} className="select-chevron" />
                  </div>
                </div>
              )}

              {/* Branch Selector (when using branch) */}
              {atopile?.source === 'branch' && (
                <div className="settings-group">
                  <label className="settings-label">
                    <span className="settings-label-title">Branch</span>
                  </label>
                  <div className="branch-search-container" ref={branchDropdownRef}>
                    <div className="branch-search-input-wrapper">
                      <Search size={12} className="branch-search-icon" />
                      <input
                        type="text"
                        className="branch-search-input"
                        placeholder="Search branches..."
                        value={branchSearchQuery}
                        onChange={(e) => {
                          setBranchSearchQuery(e.target.value);
                          setShowBranchDropdown(true);
                        }}
                        onFocus={() => setShowBranchDropdown(true)}
                        disabled={atopile?.isInstalling}
                      />
                      {atopile?.branch && !branchSearchQuery && (
                        <span className="branch-current-value">{atopile.branch}</span>
                      )}
                    </div>
                    {showBranchDropdown && (
                      <div className="branch-dropdown">
                        {(atopile?.availableBranches || ['main', 'develop'])
                          .filter(b => !branchSearchQuery || b.toLowerCase().includes(branchSearchQuery.toLowerCase()))
                          .slice(0, 15)
                          .map((b) => (
                            <button
                              key={b}
                              className={`branch-option${b === atopile?.branch ? ' active' : ''}`}
                              onClick={() => {
                                action('setAtopieBranch', { branch: b });
                                setBranchSearchQuery('');
                                setShowBranchDropdown(false);
                              }}
                            >
                              <GitBranch size={12} />
                              <span>{b}</span>
                              {b === 'main' && <span className="branch-tag">default</span>}
                            </button>
                          ))}
                        {branchSearchQuery &&
                          !(atopile?.availableBranches || []).some(b =>
                            b.toLowerCase().includes(branchSearchQuery.toLowerCase())
                          ) && (
                          <div className="branch-no-results">No branches match "{branchSearchQuery}"</div>
                        )}
                      </div>
                    )}
                  </div>
                  <span className="settings-hint">
                    Installs from git+https://github.com/atopile/atopile.git@{atopile?.branch || 'main'}
                  </span>
                </div>
              )}

              {/* Local Path Input (when using local) */}
              {atopile?.source === 'local' && (
                <div className="settings-group local-path-section">
                  <label className="settings-label">
                    <span className="settings-label-title">Local Path</span>
                  </label>

                  {/* Detected installations */}
                  {(atopile?.detectedInstallations?.length ?? 0) > 0 && (
                    <div className="detected-installations">
                      <span className="detected-label">Detected:</span>
                      {atopile?.detectedInstallations?.map((inst, i) => (
                        <button
                          key={i}
                          className={`detected-item${atopile?.localPath === inst.path ? ' active' : ''}`}
                          onClick={() => action('setAtopileLocalPath', { path: inst.path })}
                          title={inst.path}
                        >
                          <span className="detected-source">{inst.source}</span>
                          {inst.version && <span className="detected-version">v{inst.version}</span>}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Manual path input */}
                  <div className="settings-path-input">
                    <input
                      type="text"
                      className="settings-input"
                      placeholder="/path/to/atopile or ato"
                      value={atopile?.localPath || ''}
                      onChange={(e) => {
                        action('setAtopileLocalPath', { path: e.target.value });
                      }}
                    />
                    <button
                      className="path-browse-btn"
                      onClick={() => action('browseAtopilePath')}
                      title="Browse..."
                    >
                      <FolderOpen size={12} />
                    </button>
                  </div>
                </div>
              )}

              {/* Current Status */}
              {!atopile?.isInstalling && atopile?.currentVersion && (
                <div className="settings-status">
                  <Check size={12} className="status-ok" />
                  <span>
                    {atopile.source === 'local'
                      ? `Using local: ${atopile.localPath?.split('/').pop() || 'atopile'}`
                      : `v${atopile.currentVersion} installed`
                    }
                  </span>
                </div>
              )}

              <div className="settings-divider" />

              {/* Parallel Builds Setting */}
              <div className="settings-group">
                <div className="settings-row">
                  <span className="settings-label-title">Parallel builds</span>
                  <div className="settings-inline-control">
                    {maxConcurrentUseDefault ? (
                      <button
                        className="settings-value-btn"
                        onClick={() => setMaxConcurrentUseDefault(false)}
                        title="Click to set custom limit"
                      >
                        Auto ({defaultMaxConcurrent})
                      </button>
                    ) : (
                      <div className="settings-custom-input">
                        <input
                          type="number"
                          className="settings-input small"
                          min={1}
                          max={32}
                          value={maxConcurrentValue}
                          onChange={(e) => {
                            const value = Math.max(1, Math.min(32, parseInt(e.target.value) || 1));
                            setMaxConcurrentValue(value);
                            action('setMaxConcurrentSetting', {
                              useDefault: false,
                              customValue: value
                            });
                          }}
                        />
                        <button
                          className="settings-reset-btn"
                          onClick={() => {
                            setMaxConcurrentUseDefault(true);
                            action('setMaxConcurrentSetting', {
                              useDefault: true,
                              customValue: null
                            });
                          }}
                          title="Reset to auto"
                        >
                          Auto
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="settings-divider" />

              {/* Developer Settings */}
              <div className="settings-section-header">Developer</div>
              <div className="settings-group">
                <div className="settings-row">
                  <span className="settings-label-title">Show all problems</span>
                  <div className="settings-inline-control">
                    <label className="settings-toggle">
                      <input
                        type="checkbox"
                        checked={developerMode || false}
                        onChange={(e) => action('setDeveloperMode', { enabled: e.target.checked })}
                      />
                      <span className="settings-toggle-slider" />
                    </label>
                  </div>
                </div>
                <div className="settings-hint">
                  Show internal developer messages in Problems panel
                </div>
              </div>

            </div>
          )}
        </div>
      </div>
    </div>
  );
}
